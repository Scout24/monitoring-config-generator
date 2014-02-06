from datetime import datetime
import logging
import logging.handlers
import optparse
import os
import sys
from time import localtime, strftime


from .exceptions import (MonitoringConfigGeneratorException,
                         ConfigurationContainsUndefinedVariables,
                         )
from .settings import CONFIG, ETAG_COMMENT
from .readers import read_config
from .yaml_config import YamlConfig


MON_CONF_GEN_COMMENT = '# Created by MonitoringConfigGenerator'


class MonitoringConfigGenerator(object):

    def __init__(self, args=None):
        args = [args] if isinstance(args, basestring) else []
        self.create_logger()

        usage = '''
%prog reads the yaml config of a host via file or http and generates nagios/icinga config from that
%prog [hostname|filename]

Configuration file can be specified in MONITORING_CONFIG_GENERATOR_CONFIG environment variable
'''
        parser = optparse.OptionParser(usage=usage)
        parser.add_option("--debug",
                          dest="debug",
                          action="store_true",
                          default=False,
                          help="Enable debug logging [%default]")

        parser.add_option("--targetdir",
                          dest="target_dir",
                          action="store",
                          default=CONFIG['TARGET_DIR'],
                          type="string",
                          help="Directory for generated config files")

        parser.add_option("--skip-checks",
                          dest="skip_checks",
                          action="store_true",
                          default=False,
                          help="Skip checks on generated config")

        self.options, self.args = parser.parse_args(args)

        if self.options.debug:
            self.output_debug_log_to_console()

        self.target_dir = self.options.target_dir
        if not os.path.isdir(self.target_dir):
            raise MonitoringConfigGeneratorException("%s is not a directory" % self.target_dir)
        self.logger.debug("Using %s as target dir" % self.target_dir)

        if len(self.args) < 1:
            msg = "Need to get at least one host to operate on"
            self.logger.fatal(msg)
            raise MonitoringConfigGeneratorException(msg)
        self.logger.debug("Args: %s" % self.args)
        self.source = self.args[0]
        self.logger.info("MonitoringConfigGenerator start: reading from %s, writing to %s" % (self.source, self.target_dir))

    def create_logger(self):
        self.logger = logging.getLogger()
        if len(self.logger.handlers) == 0:
            try:
                loghandler = logging.handlers.SysLogHandler(address='/dev/log')
            except:
                # if we cannot setup a SysLogger (maybe we are running on Win) log to console as last resort
                loghandler = logging.StreamHandler()

            format_string = 'monitoring_config_generator[' + str(os.getpid()) + ']: %(levelname)s: %(message)s'
            loghandler.setFormatter(logging.Formatter(format_string))
            self.logger.addHandler(loghandler)
        self.logger.setLevel(logging.INFO)

    def output_debug_log_to_console(self):
        loghandler = logging.StreamHandler()
        loghandler.setFormatter(
            logging.Formatter('MonitoringConfigGenerator[%(filename)s:%(lineno)d]: %(levelname)s: %(message)s'))
        self.logger.addHandler(loghandler)
        self.logger.setLevel(logging.DEBUG)
        self.logger.debug("Debug logging enabled via command line")

    def output_path(self, hostname):
        return os.path.join(self.target_dir, hostname + '.cfg')

    def generate(self):
        raw_yaml_config, etag, mtime = read_config(self.source)

        if raw_yaml_config is None:
            return 1

        try:
            self.yaml_config = YamlConfig(raw_yaml_config,
                                          skip_checks=self.options.skip_checks)
        except ConfigurationContainsUndefinedVariables:
            self.logger.error("Configuration contained undefined variables!")
            return 1

        host_name = self.yaml_config.host_name
        if not host_name:
            raise Exception('hostname not found')
        self.output_path = self.output_path(host_name)
        self.etag = etag
        # TODO: compare ETag and mtime
        #if not self.input_reader.config_changed:
        #    self.logger.debug("Config didn't change, keeping old version")
        #    return 0
        self.write_output()
        return 0

    def write_output(self):
        self.output_writer = OutputWriter(self.output_path)
        self.output_writer.indent = CONFIG['INDENT']
        self.output_writer.etag = self.etag
        self.output_writer.write_icinga_config(self.yaml_config)


class YamlToIcinga(object):

    def __init__(self, yaml_config, indent, etag):
        self.icinga_lines = []
        self.indent = indent
        self.etag = etag
        self.write_header()
        self.write_section('host', yaml_config.host)
        for service in yaml_config.services:
            self.write_section('service', service)

    def write_line(self, line):
        self.icinga_lines.append(line)

    def write_header(self):
        timeString = strftime("%Y-%m-%d %H:%M:%S", localtime())
        self.write_line("%s on %s" % (MON_CONF_GEN_COMMENT, timeString))
        if self.etag is not None:
            self.write_line("%s%s" % (ETAG_COMMENT, self.etag))

    def write_section(self, section_name, section_data):
        self.write_line("")
        self.write_line("define %s {" % section_name)
        sorted_keys = section_data.keys()
        sorted_keys.sort()
        for key in sorted_keys:
            value = section_data[key]
            self.icinga_lines.append(("%s%-45s%s" % (self.indent, key, self.value_to_icinga(value))))
        self.write_line("}")

    @staticmethod
    def value_to_icinga(value):
        """Convert a scalar or list to Icinga value format. Lists are concatenated by ,
        and empty (None) values produce an empty string"""
        if isinstance(value, list):
            # explicitly set None values to empty string
            return ",".join([str(x) if (x is not None) else "" for x in value])
        else:
            return str(value)


class OutputWriter(object):

    def __init__(self, output_file):
        self.logger = logging.getLogger("OutputWriter")
        self.output_file = output_file
        default_indent = ' ' * 8
        self.indent = default_indent
        self.etag = None

    def write_icinga_config(self, yaml_config):
        lines = YamlToIcinga(yaml_config, self.indent, self.etag).icinga_lines
        with open(self.output_file, 'w') as f:
            for line in lines:
                f.write(line + "\n")
        self.logger.debug("Created %s" % self.output_file)


def main_method():
    start_time = datetime.now()
    try:
        exit_code = MonitoringConfigGenerator(sys.argv[1:]).generate()
    except SystemExit as e:
        exit_code = e.code
    except BaseException as e:
        # logging was initialized inside MonitoringConfigGenerator, that's why we will only get the logger now
        log = logging.getLogger()
        log.exception(e)
        if log.level is not logging.DEBUG:
            # debug log already prints error, don't print it again
            print >>sys.stderr, 'ERROR: %s' % e.message
        exit_code = 1
    finally:
        stop_time = datetime.now()
        logging.getLogger().info("finished in %s" % (stop_time - start_time))
    sys.exit(exit_code)

if __name__ == '__main__':
    main_method()
