import os
import re
import shutil
import unittest

import yaml

from monitoring_config_generator.exceptions import ConfigurationContainsUndefinedVariables, UnknownSectionException, \
    MandatoryDirectiveMissingException, HostNamesNotEqualException, ServiceDescriptionNotUniqueException
from monitoring_config_generator.settings import CONFIG
from monitoring_config_generator.yaml_tools.config import YamlConfig
from test_logger import init_test_logger


class YamlConfigTest(unittest.TestCase):
    def setUp(self):
        self.test_directory = "testdata"
        shutil.rmtree(CONFIG["TARGET_DIR"], True)
        os.mkdir(CONFIG["TARGET_DIR"])

    init_test_logger()

    def run_config_gen(self, yaml_config_str):
        yaml_parsed = yaml.load(yaml_config_str)
        yaml_config = YamlConfig(yaml_parsed)
        self.host_definition = yaml_config.host
        self.service_definitions = yaml_config.services

    def test_reads_a_valid_yaml_configuration_without_errors(self):
        input_yaml = '''
            host:
                host_name: host.domain.tld
            services:
                s1:
                   check_command: any_check_command
                   host_name: host.domain.tld
                   service_description: any_service_name
            defaults:
                check_period: 2
                max_check_attempts: 5
                notification_interval: 3
                notification_period: 4
                check_interval: 6
                retry_interval: 7
        '''
        self.run_config_gen(input_yaml)

    def test_generates_host_definition_from_yaml_with_all_mandatory_fields(self):
        input_yaml = '''
            host:
                host_name: host.domain.tld
                max_check_attempts: 5
                check_period: 24x7
                notification_interval: 3
                notification_period: 4
            services:
                service_1:
                    host_name: host.domain.tld
                    service_description: service_description
                    check_command: check_command
                    max_check_attempts: 2
                    check_period: 4
                    notification_interval: 3
                    notification_period: 4
        '''
        self.run_config_gen(input_yaml)

        self.assertEquals(self.host_definition.get("host_name"), "host.domain.tld")
        self.assertEquals(self.host_definition.get("check_period"), "24x7")
        self.assertEquals(self.host_definition.get("max_check_attempts"), 5)
        self.assertEquals(self.host_definition.get("notification_interval"), 3)
        self.assertEquals(self.host_definition.get("notification_period"), 4)
        self.assertEquals(self.service_definitions[0].get("_service_id"), "service_1")
        self.assertEquals(self.service_definitions[0].get("host_name"), "host.domain.tld")
        self.assertEquals(self.service_definitions[0].get("service_description"), "service_description")
        self.assertEquals(self.service_definitions[0].get("check_command"), "check_command")
        self.assertEquals(self.service_definitions[0].get("max_check_attempts"), 2)
        self.assertEquals(self.service_definitions[0].get("notification_interval"), 3)
        self.assertEquals(self.service_definitions[0].get("notification_period"), 4)


    def test_raises_an_error_if_the_hostname_for_host_and_service_does_not_match(self):
        input_yaml = '''
            host:
                host_name: host.domain.tld
            services:
                s1:
                   host_name: other.domain.tld
            defaults:
                check_period: 2
                max_check_attempts: 5
                notification_interval: 3
                notification_period: 4
                check_interval: 6
                retry_interval: 7
                check_command: any_check_command
                service_description: any_service_name
        '''

        self.assertRaises(HostNamesNotEqualException, self.run_config_gen, input_yaml)

    def test_generates_no_host_and_service_definition_if_there_is_not_at_least_one_service_configuration_given(self):
        input_yaml = '''
            defaults:
                host_name: host.domain.tld
            host:
                max_check_attempts: 5
                check_period: 24x7
                notification_interval: 3
                notification_period: 1
        '''

        self.run_config_gen(input_yaml)

        self.assertEquals(self.host_definition, None)
        self.assertEquals(self.service_definitions, [])

    def test_that_defaults_are_used_for_generation_of_service_and_host_definition(self):
        input_yaml = '''
            defaults:
                host_name: host.domain.tld
                check_period: 2
                max_check_attempts: 5
                notification_interval: 3
                notification_period: 4
                check_interval: 6
                retry_interval: 7
                check_command: any_check_command
                service_description: any_service_name
            services:
                service_1:
                  service_description: service_1
        '''

        self.run_config_gen(input_yaml)

        self.assertEquals(self.host_definition.get("host_name"), "host.domain.tld")
        self.assertEquals(self.host_definition.get("check_period"), 2)
        self.assertEquals(self.host_definition.get("max_check_attempts"), 5)
        self.assertEquals(self.host_definition.get("notification_interval"), 3)
        self.assertEquals(self.host_definition.get("notification_period"), 4)
        self.assertEquals(self.service_definitions[0].get("host_name"), "host.domain.tld")
        self.assertEquals(self.service_definitions[0].get("service_description"), "service_1")
        self.assertEquals(self.service_definitions[0].get("check_command"), "any_check_command")
        self.assertEquals(self.service_definitions[0].get("max_check_attempts"), 5)
        self.assertEquals(self.service_definitions[0].get("notification_interval"), 3)
        self.assertEquals(self.service_definitions[0].get("notification_period"), 4)

    def test_raises_an_error_if_there_are_any_undefined_variables(self):
        input_yaml = """
            defaults:
                host_name: host.domain.tld
                check_period: ${VARIABLE}
                max_check_attempts: 5
                notification_interval: 3
                notification_period: 4
                check_interval: 6
                retry_interval: 7
                check_command: any_check_command
                service_description: any_service_name
            host:
                notification_options: u,d
            services:
                service_1:
                    service_description: any_service
        """

        self.assertRaises(ConfigurationContainsUndefinedVariables, self.run_config_gen, input_yaml)

    def test_undefined_variables_exception_contains_the_list_of_undefined_variables(self):
        input_yaml = """
            defaults:
                host_name: host.domain.tld
                check_period: any_long_string_${VARIABLE1}_suffix
                max_check_attempts: 5
                notification_interval: 3
                notification_period: 4
                check_interval: 6
                retry_interval: 7
                check_command: any_check_command
                service_description: any_service_name
            host:
                notification_options: u,d
            services:
                service_1:
                    service_description: any_long:string_${VARIABLE2}_suffix
        """

        try:
            self.run_config_gen(input_yaml)
        except ConfigurationContainsUndefinedVariables as e:
            self.assertTrue(re.compile('\'\$\{VARIABLE2\}, \$\{VARIABLE1\}\'').search(str(e)))


    def test_raises_an_error_if_there_are_any_not_supported_sections(self):
        input_yaml = '''
            unsupported:
                whatever
        '''
        self.assertRaises(UnknownSectionException, self.run_config_gen, input_yaml)

    def test_raises_an_error_if_there_is_a_mandatory_service_field_missing(self):
        input_yaml = '''
            defaults:
                host_name: host.domain.tld
                check_period: 2
                max_check_attempts: 5
                notification_interval: 3
                notification_period: 4
                check_interval: 6
                retry_interval: 7
                check_command: any_check_command
            services:
                s1:
                   missing_field: service_description
        '''
        self.assertRaises(MandatoryDirectiveMissingException, self.run_config_gen, input_yaml)

    def test_raises_an_error_if_there_is_a_mandatory_host_field_missing(self):
        input_yaml = '''
            defaults:
                check_period: 2
                max_check_attempts: 5
                notification_interval: 3
                notification_period: 4
                check_interval: 6
                retry_interval: 7
                check_command: any_check_command
            host:
                missing_field: host_name
            services:
                service_1:
                    service_description: service_description
        '''
        self.assertRaises(MandatoryDirectiveMissingException, self.run_config_gen, input_yaml)

    def test_raises_an_error_if_the_service_description_is_not_unique(self):
        input_yaml = '''
            defaults:
                host_name: host.domain.tld
                check_period: 2
                max_check_attempts: 5
                notification_interval: 3
                notification_period: 4
                check_interval: 6
                retry_interval: 7
                check_command: any_check_command
            host:
                host_name: host.domain.tld
            services:
                s1:
                   service_description: service 1
                s2:
                   service_description: service 1
        '''
        self.assertRaises(ServiceDescriptionNotUniqueException, self.run_config_gen, input_yaml)
