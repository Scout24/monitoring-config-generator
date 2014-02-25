"""monconfgenerator

Creates an Icinga monitoring configuration. It does it by querying an URL from
which it receives a specially formatted yaml file. This file is transformed into
a valid Icinga configuration file.
If no URL is given it reads it's default configuration from file system. The
configuration file is: /etc/monitoring_config_generator/config.yaml'

Usage:
  monconfgenerator [--debug] [--targetdir=<directory>] [--skip-checks] [URL]
  monconfgenerator -h

Options:
  -h                Show this message.
  --debug           Print additional information.
  --targetdir=DIR   The generated Icinga monitoring configuration is written
                    into this directory. If no target directory is given its
                    value is read from /etc/monitoring_config_generator/config.yaml
  --skip-checks     Do not run checks on the yaml file received from the URL.

"""
from datetime import datetime
import logging
import logging.handlers
import os
import sys

from docopt import docopt

from .exceptions import (MonitoringConfigGeneratorException,
                         ConfigurationContainsUndefinedVariables,
                         NoSuchHostname)
from monitoring_config_generator.yaml_tools.readers import Header, read_config
from monitoring_config_generator.yaml_tools.config import YamlConfig
from .settings import CONFIG


CONFIG_WRITTEN = 0
ERROR = 1
CONFIG_NOT_WRITTEN = 2


class MonitoringConfigGenerator(object):
    def __init__(self, url, debug_enabled=False, target_dir=CONFIG['TARGET_DIR'], skip_checks=False):
        self.skip_checks = skip_checks
        self.target_dir = target_dir
        self.source = url

        self.create_logger()

        if debug_enabled:
            self.output_debug_log_to_console()

        if not os.path.isdir(self.target_dir):
            raise MonitoringConfigGeneratorException("%s is not a directory" % self.target_dir)

        self.logger.debug("Using %s as target dir" % self.target_dir)

        self.logger.debug("Using URL: %s" % self.source)
        self.logger.info(
            "MonitoringConfigGenerator start: reading from %s, writing to %s" % (self.source, self.target_dir))

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

    def _is_newer(self, header, host_name):
        if not host_name:
            raise NoSuchHostname('hostname not found')
        output_path = self.output_path(host_name)
        old_header = Header.parse(output_path)
        return header.is_newer_than(old_header)

    def write_monitoring_config(self, header, yaml_config):
        host_name = yaml_config.host_name
        output_path = self.output_path(host_name)
        self.write_output(output_path, yaml_config, header)

    def generate(self):
        raw_yaml_config, header = read_config(self.source)
        if raw_yaml_config is None:
            return ERROR

        try:
            yaml_config = YamlConfig(raw_yaml_config,
                                     skip_checks=self.skip_checks)
        except ConfigurationContainsUndefinedVariables:
            self.logger.error("Configuration contained undefined variables!")
            return ERROR

        if yaml_config.host and self._is_newer(header, yaml_config.host_name):
            self.write_monitoring_config(header, yaml_config)
            return CONFIG_WRITTEN
        else:
            return CONFIG_NOT_WRITTEN

    @staticmethod
    def write_output(output_path, yaml_config, header):
        lines = YamlToIcinga(yaml_config, header).icinga_lines
        output_writer = OutputWriter(output_path)
        output_writer.write_lines(lines)


class YamlToIcinga(object):
    def __init__(self, yaml_config, header):
        self.icinga_lines = []
        self.indent = CONFIG['INDENT']
        self.icinga_lines.extend(header.serialize())
        self.write_section('host', yaml_config.host)
        for service in yaml_config.services:
            self.write_section('service', service)

    def write_line(self, line):
        self.icinga_lines.append(line)

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

    def write_lines(self, lines):
        with open(self.output_file, 'w') as f:
            for line in lines:
                f.write(line + "\n")
        self.logger.debug("Created %s" % self.output_file)


def generate_config():
    arg = docopt(__doc__, version='0.1.0')
    start_time = datetime.now()
    try:
        exit_code = MonitoringConfigGenerator(arg['URL'],
                                              arg['--debug'],
                                              arg['--targetdir'],
                                              arg['--skip-checks']).generate()
    except SystemExit as e:
        exit_code = e.code
    except BaseException as e:
        # logging was initialized inside MonitoringConfigGenerator, that's why we will only get the logger now
        log = logging.getLogger()
        log.error(e)
        exit_code = 1
    finally:
        stop_time = datetime.now()
        logging.getLogger().info("finished in %s" % (stop_time - start_time))
    sys.exit(exit_code)


if __name__ == '__main__':
    generate_config()
