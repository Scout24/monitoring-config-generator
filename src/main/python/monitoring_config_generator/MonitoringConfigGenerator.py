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
import os
import sys

from docopt import docopt

from monitoring_config_generator.exceptions import MonitoringConfigGeneratorException, \
    ConfigurationContainsUndefinedVariables, NoSuchHostname, HostUnreachableException
from monitoring_config_generator import set_log_level_to_debug
from monitoring_config_generator.yaml_tools.readers import Header, read_config
from monitoring_config_generator.yaml_tools.config import YamlConfig
from monitoring_config_generator.settings import CONFIG


EXIT_CODE_CONFIG_WRITTEN = 0
EXIT_CODE_ERROR = 1
EXIT_CODE_NOT_WRITTEN = 2

LOG = logging.getLogger("monconfgenerator")


class MonitoringConfigGenerator(object):
    def __init__(self, url, debug_enabled=False, target_dir=None, skip_checks=False):
        self.skip_checks = skip_checks
        self.target_dir = target_dir if target_dir else CONFIG['TARGET_DIR']
        self.source = url

        if debug_enabled:
            set_log_level_to_debug()

        if not self.target_dir or not os.path.isdir(self.target_dir):
            raise MonitoringConfigGeneratorException("%s is not a directory" % self.target_dir)

        LOG.debug("Using %s as target dir" % self.target_dir)
        LOG.debug("Using URL: %s" % self.source)
        LOG.debug("MonitoringConfigGenerator start: reading from %s, writing to %s" %
                  (self.source, self.target_dir))

    def _is_newer(self, header_source, hostname):
        if not hostname:
            raise NoSuchHostname('hostname not found')
        output_path = self.output_path(self.create_filename(hostname))
        old_header = Header.parse(output_path)
        return header_source.is_newer_than(old_header)

    def output_path(self, file_name):
        return os.path.join(self.target_dir, file_name)

    def write_output(self, file_name, yaml_icinga):
        lines = yaml_icinga.icinga_lines
        output_writer = OutputWriter(self.output_path(file_name))
        output_writer.write_lines(lines)

    @staticmethod
    def create_filename(hostname):
        name = '%s.cfg' % hostname
        if name != os.path.basename(name):
            msg = "Directory traversal attempt detected for host name %r"
            raise Exception(msg % hostname)
        return name

    def generate(self):
        file_name = None
        raw_yaml_config, header_source = read_config(self.source)

        if raw_yaml_config is None:
            raise SystemExit("Raw yaml config from source '%s' is 'None'." % self.source)

        yaml_config = YamlConfig(raw_yaml_config,
                                 skip_checks=self.skip_checks)

        if yaml_config.host and self._is_newer(header_source, yaml_config.host_name):
            file_name = self.create_filename(yaml_config.host_name)
            yaml_icinga = YamlToIcinga(yaml_config, header_source)
            self.write_output(file_name, yaml_icinga)

        if file_name:
            LOG.info("Icinga config file '%s' created." % file_name)

        return file_name

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
        self.output_file = output_file

    def write_lines(self, lines):
        with open(self.output_file, 'w') as f:
            for line in lines:
                f.write(line + "\n")
        LOG.debug("Created %s" % self.output_file)


def generate_config():
    arg = docopt(__doc__, version='0.1.0')
    start_time = datetime.now()
    try:
        file_name = MonitoringConfigGenerator(arg['URL'],
                                              arg['--debug'],
                                              arg['--targetdir'],
                                              arg['--skip-checks']).generate()
        exit_code = EXIT_CODE_CONFIG_WRITTEN if file_name else EXIT_CODE_NOT_WRITTEN
    except HostUnreachableException:
        LOG.warn("Target url {0} unreachable. Could not get yaml config!".format(arg['URL']))
        exit_code = EXIT_CODE_NOT_WRITTEN
    except ConfigurationContainsUndefinedVariables:
        LOG.error("Configuration contained undefined variables!")
        exit_code = EXIT_CODE_ERROR
    except SystemExit as e:
        exit_code = e.code
    except BaseException as e:
        LOG.error(e)
        exit_code = EXIT_CODE_ERROR
    finally:
        stop_time = datetime.now()
        LOG.info("finished in %s" % (stop_time - start_time))
    sys.exit(exit_code)


if __name__ == '__main__':
    generate_config()
