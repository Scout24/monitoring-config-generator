import logging


from .exceptions import (MonitoringConfigGeneratorException,
                         ConfigurationContainsUndefinedVariables,
                         UnknownSectionException,
                         MandatoryDirectiveMissingException,
                         HostNamesNotEqualException,
                         ServiceDescriptionNotUniqueException,
                         )
from .settings import ICINGA_HOST_DIRECTIVES, ICINGA_SERVICE_DIRECTIVES
from .yaml_merger import dict_merge


SUPPORTED_SECTIONS = ['defaults', 'variables', 'host', 'services']


class YamlConfig(object):

    def __init__(self, yaml_config, skip_checks=False):
        self.logger = logging.getLogger("IcingaGenerator")
        self.yaml_config = yaml_config
        self.skip_checks = skip_checks
        self.host = None
        self.services = []
        self.generate()

    @property
    def host_name(self):
        return self.host['host_name']

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

    def _generate_monitoring_configuration(self, host_definition, service_definition):
        self.generate_host_definition(host_definition)
        self.generate_service_definitions(service_definition)
        self.run_post_generation_checks()
        self.configuration_contains_undefined_variables()

    def generate(self):
        self.run_pre_generation_checks()

        host_definition = self.yaml_config.get('host', {})
        service_definition = self.yaml_config.get("services", {})

        if host_definition or service_definition:
            self._generate_monitoring_configuration(host_definition, service_definition)

    def generate_host_definition(self, host_definition):
        self.host = self.section_with_defaults(host_definition)
        self.apply_variables(self.host)

    def generate_service_definitions(self, service_definition):
        if not isinstance(service_definition, dict):
            raise MonitoringConfigGeneratorException("services must be a dict")
        for yaml_service_id in sorted(service_definition.keys()):
            self.services.append(self.generate_service_definition(service_definition[yaml_service_id], yaml_service_id))

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

    def host_configuration_contains_undefined_variables(self):
        host_settings = self.host
        for setting_key in host_settings:
            if "${" in str(host_settings[setting_key]):
                return True
        return False

    def service_configuration_contains_undefined_variables(self):
        for settings_of_single_service in self.services:
            for setting_key in settings_of_single_service:
                if "${" in str(settings_of_single_service[setting_key]):
                    return True
        return False

    def configuration_contains_undefined_variables(self):
        if self.host_configuration_contains_undefined_variables() or \
                self.service_configuration_contains_undefined_variables():
            raise ConfigurationContainsUndefinedVariables
