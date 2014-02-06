from datetime import datetime
import logging
import logging.handlers
import optparse
import os
import sys
from time import localtime, strftime


from MonitoringConfigGeneratorExceptions import *
from settings import CONFIG, ICINGA_HOST_DIRECTIVES, ICINGA_SERVICE_DIRECTIVES, ETAG_COMMENT
from yaml_merger import dict_merge
from .readers import InputReader

MON_CONF_GEN_COMMENT = '# Created by MonitoringConfigGenerator'
SUPPORTED_SECTIONS = ['defaults', 'variables', 'host', 'services']


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
        source = self.args[0]
        self.logger.info("MonitoringConfigGenerator start: reading from %s, writing to %s" % (source, self.target_dir))
        self.input_reader = InputReader(source, self.target_dir)

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

    def generate(self):
        self.input_reader.read_input()

        if not self.input_reader.config_changed:
            self.logger.debug("Config didn't change, keeping old version")
            return 0

        self.yaml_config = self.input_reader.yaml_config
        if self.yaml_config is None:
            return 1

        self.icinga_generator = IcingaGenerator(self.yaml_config)
        self.icinga_generator.skip_checks = self.options.skip_checks
        self.icinga_generator.generate()
        if(not self.configuration_contains_undefined_variables()):
            self.write_output()
            return 0
        else:
            self.logger.error("Configuration contained undefined variables!")
            return 1

    def host_configuration_contains_undefined_variables(self):
        host_settings = self.icinga_generator.host
        for setting_key in host_settings:
            if "${" in str(host_settings[setting_key]):
                return True
        return False

    def service_configuration_contains_undefined_variables(self):
        for settings_of_single_service in self.icinga_generator.services:
            for setting_key in settings_of_single_service:
                if "${" in str(settings_of_single_service[setting_key]):
                    return True
        return False

    def configuration_contains_undefined_variables(self):
        return self.host_configuration_contains_undefined_variables() or \
            self.service_configuration_contains_undefined_variables()

    def write_output(self):
        self.output_writer = OutputWriter(self.input_reader.output_path)
        self.output_writer.indent = CONFIG['INDENT']
        self.output_writer.etag = self.input_reader.etag
        self.output_writer.write_icinga_config(self.icinga_generator)


class IcingaGenerator(object):
    def __init__(self, yaml_config):
        self.logger = logging.getLogger("IcingaGenerator")
        self.yaml_config = yaml_config
        self.skip_checks = False
        self.services = []

    def run_pre_generation_checks(self):
        if not self.skip_checks:
            # check for unknown sections
            if self.yaml_config is not None:
                for section in self.yaml_config:
                    if not section in SUPPORTED_SECTIONS:
                        raise UnknownSectionException("I don't know how to handle section '%s' " % section)

    def run_post_generation_checks(self):
        if not self.skip_checks:
            # check for all directives in host
            for directive in ICINGA_HOST_DIRECTIVES:
                if not directive in self.host:
                    raise MandatoryDirectiveMissingException("Mandatory directive %s is missing from host-section" %
                                                             directive)

            # check for all directives in services
            for directive in ICINGA_SERVICE_DIRECTIVES:
                for service in self.services:
                    if not directive in service:
                        raise MandatoryDirectiveMissingException("Mandatory directive %s is missing from service %s" %
                                                                 (directive, service))

            # check host_name equal
            all_host_names = set([service["host_name"] for service in self.services])
            all_host_names.add(self.host["host_name"])

            if len(all_host_names) > 1:
                raise HostNamesNotEqualException("More than one host_name was generated: %s" % all_host_names)

            # check service_description is unique
            used_descriptions = set()
            multiple_descriptions = set()

            for service in self.services:
                service_description = service["service_description"]
                if service_description in used_descriptions:
                    multiple_descriptions.add(service_description)
                used_descriptions.add(service_description)

            if len(multiple_descriptions) > 0:
                raise ServiceDescriptionNotUniqueException("Service description %s used for more than one service" %
                                                           multiple_descriptions)

    def generate(self):
        self.run_pre_generation_checks()
        self.generate_host_definition()
        self.generate_service_definitions()
        self.run_post_generation_checks()

    def generate_host_definition(self):
        self.host = self.section_with_defaults(self.yaml_config.get('host', {}))
        self.apply_variables(self.host)

    def generate_service_definitions(self):
        yaml_services = self.yaml_config.get("services", {})
        if not isinstance(yaml_services, dict):
            raise MonitoringConfigGeneratorException("services must be a dict")
        for yaml_service_id in sorted(yaml_services.keys()):
            self.services.append(self.generate_service_definition(yaml_services[yaml_service_id], yaml_service_id))

    def generate_service_definition(self, yaml_service, yaml_service_id):
        service_definition = self.section_with_defaults(yaml_service)
        service_definition["_service_id"] = yaml_service_id
        self.apply_variables(service_definition)
        return service_definition

    def section_with_defaults(self, section):
        new_section = {}
        # put defaults in section first
        if 'defaults' in self.yaml_config:
            dict_merge(new_section, self.yaml_config['defaults'])
        # overwrite defaults with concrete values
        dict_merge(new_section, section)
        return new_section

    def apply_variables(self, section):
        variables = self.yaml_config.get('variables', {})

        sorted_keys = section.keys()
        sorted_keys.sort()

        while True:
            variables_applied = False
            for variable_name in variables.keys():
                variable_syntax = "${%s}" % variable_name
                variable_value = str(variables[variable_name])

                # example for: x = 3:
                # - variable_name == 'x'
                # - variable_value == '3'
                # - variable_syntax = '${x}'

                for key in sorted_keys:
                    value = section.get(key)
                    # yaml values are not always strings, they can be ints for instance
                    if isinstance(value, str) and variable_syntax in value:
                        section[key] = value.replace(variable_syntax, variable_value)
                        variables_applied = True

            if not variables_applied:
                break


class YamlToIcinga(object):

    def __init__(self, icinga_generator, indent, etag):
        self.icinga_lines = []
        self.indent = indent
        self.etag = etag
        self.write_header()
        self.write_section('host', icinga_generator.host)
        for service in icinga_generator.services:
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

    def write_icinga_config(self, icinga_generator):
        lines = YamlToIcinga(icinga_generator, self.indent, self.etag).icinga_lines
        with open(self.output_file, 'w') as f:
            for line in lines:
                f.write(line + "\n")
            f.close()
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
