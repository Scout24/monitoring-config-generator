import unittest
import os
import shutil

import yaml

# load test configuration
os.environ['MONITORING_CONFIG_GENERATOR_CONFIG'] = "testdata/testconfig.yaml"
from monitoring_config_generator.settings import CONFIG
from monitoring_config_generator.MonitoringConfigGenerator import MonitoringConfigGenerator, \
    IcingaGenerator, MON_CONF_GEN_COMMENT
from monitoring_config_generator.MonitoringConfigGeneratorExceptions import *
from TestLogger import init_test_logger

class Test(unittest.TestCase):

    testDir = "testdata"
    shutil.rmtree(CONFIG["TARGET_DIR"], True)
    os.mkdir(CONFIG["TARGET_DIR"])

    init_test_logger()
    
    def run_config_generator_on_directory(self, input_dir):
        """convenience function: if input_dir contains exactly one yaml and on .cfg file it will run the generator
           on the yaml file and compare to the .cfg file"""
        dir_for_this_test = os.path.join(self.testDir, input_dir)
        all_yaml = [filename for filename in os.listdir(dir_for_this_test) if filename.endswith(".yaml")]
        all_cfg = [filename for filename in os.listdir(dir_for_this_test) if filename.endswith(".cfg")]
        self.assertEquals(1, len(all_yaml))
        self.assertEquals(1, len(all_cfg))
        self.run_full_config_gen(input_dir, all_yaml[0], all_cfg[0])

    def run_full_config_gen(self, input_dir, yaml_file, config_file):
        """this will run the config gen on the yaml_file and compare the generated output to config_file"""
        this_test_dir = os.path.join(self.testDir, input_dir)
        input_path = os.path.abspath(os.path.join(this_test_dir, yaml_file))
        MonitoringConfigGenerator(input_path).generate()

        output_path = os.path.join(CONFIG['TARGET_DIR'], config_file)
        expected_output_path = os.path.join(this_test_dir, config_file)

        self.assert_no_undefined_variables(output_path)
        self.assert_that_contents_of_files_is_identical(output_path, expected_output_path)

    def assert_no_undefined_variables(self, filename):
        generated_config_file = file(filename)
        for line in generated_config_file:
            self.assertFalse("${" in line,"found undefined variable in " + filename)

    def get_yaml_file_from_directory(self,directory): 
        input_directory = os.path.join(self.testDir, directory)
        all_yaml = [filename for filename in os.listdir(input_directory) if filename.endswith(".yaml")]
        self.assertEquals(1, len(all_yaml))
        yaml_file = all_yaml[0]
        yaml_file_with_path = os.path.abspath(os.path.join(input_directory, yaml_file))
        return yaml_file_with_path

    def run_config_generator_for_invalid_file(self, input_dir, generated_configuration_filename): 
        yaml_file = self.get_yaml_file_from_directory(input_dir) 
        MonitoringConfigGenerator(yaml_file).generate()
        output_path = os.path.join(CONFIG['TARGET_DIR'],generated_configuration_filename)
        self.assertFalse(os.path.exists(output_path),"Generator generated file for undefined variables")
 

    def test_generated_config_with_missing__variable(self):
        self.run_config_generator_for_invalid_file("itest_testhost08_variables","testhost08.other.domain.cfg")
    
    def test_generated_config_with_missing_service_variable(self):
        self.run_config_generator_for_invalid_file("itest_testhost09_variables","testhost09.other.domain.cfg")

    def test_generates_config_from_new_file(self):
        self.run_config_generator_on_directory("itest_testhost03_new_format")

    def test_generated_config_using_defaults(self):
        self.run_config_generator_on_directory("itest_testhost04_defaults")

    def test_generated_config_using_defaults_and_variables(self):
        self.run_config_generator_on_directory("itest_testhost05_variables")
    
    def test_generated_config_with_list_with_quotes(self):
        self.run_config_generator_on_directory("itest_testhost10_quotes")

    
    def test_some_edge_cases(self):
        self.run_config_generator_on_directory("itest_testhost06_defaults_before_variables")
    

    def assert_that_contents_of_files_is_identical(self, actualFileName, expectedFileName):
        linesActual = open(actualFileName, 'r').readlines()
        linesExpected = open(expectedFileName, 'r').readlines()
        lenActual = len(linesActual)
        lenExpected = len(linesExpected)

        self.assertEquals(lenActual,
                          lenExpected,
                          "number of lines not equal (expected=%s, actual=%s)" % (lenExpected, lenActual))

        for index in range(lenExpected):
            lineActual = linesActual[index]
            lineExpected = linesExpected[index]

            # special handling for the the header line
            # because "Created by ... " contains a date, so it will not match exactly
            if lineExpected.startswith(MON_CONF_GEN_COMMENT):
                # so if it is the line containing the date we will only compare the start of the line
                self.assertTrue(lineActual.startswith(MON_CONF_GEN_COMMENT))
            else:
                # other lines will be compared completely of course
                self.assertEquals(lineActual,
                                  lineExpected,
                                  "Line #%d does not match (expected='%s', actual='%s'" %
                                      (index, lineExpected, lineActual))

    def run_config_gen(self, yamlConfig):
        yaml_parsed = yaml.load(yamlConfig)
        icinga_generator = IcingaGenerator(yaml_parsed)
        icinga_generator.generate()
        self.host_definition = icinga_generator.host
        self.service_definitions = icinga_generator.services

    def test_generates_icinga_config(self):
        input_yaml = '''
            host:
                address: testhost01.some.domain
                host_name: testhost01

            services:
                s1:
                   check_command: check_graphite_disk_usage!_boot!90!95
                   host_name: testhost01
                   service_description: service 1
            defaults:
                check_period: 2
                max_check_attempts: 5
                notification_interval: 3
                notification_period: 4
                check_interval: 6
                retry_interval: 7
        '''
        self.run_config_gen(input_yaml)

    def test_generates_host_definition(self):
        input_yaml = '''
            host:
                check_period:   24x7
                max_check_attempts:    5
                host_name: testhost01.sub.domain
                max_check_attempts: 5
                notification_interval: 3
                notification_period: 4
                check_interval: 6
                retry_interval: 7
        '''
        self.run_config_gen(input_yaml)
        self.assertEquals(self.host_definition.get("check_period"), "24x7")
        self.assertEquals(self.host_definition.get("max_check_attempts"), 5)

    def test_default_values_are_no_longer_generated(self):
        """address and host_name used to be generated in the old format, but are no longer"""
        input_yaml = '''
            defaults:
                host_name: testhost01.sub.domain
            host:
                check_period:   24x7
                max_check_attempts:    5
                notification_interval: #
                notification_period: #
        '''
        host_name = "testhost01.sub.domain"
        self.run_config_gen(input_yaml)
        self.assertEquals(None, self.host_definition.get("address"))
        self.assertEquals(self.host_definition.get("host_name"), host_name)
        self.assertEquals(self.host_definition.get("check_period"), "24x7")
        self.assertEquals(self.host_definition.get("max_check_attempts"), 5)

    def test_that_service_only_defaults_are_not_used_for_generation_of_host_definition(self):
        input_yaml = '''
            defaults:
                host_name: testhost01
                hostgroup_name:    group name
                service_description: desc of service
                is_volatile:    1
                check_period: 2
                max_check_attempts:    5
                notification_interval: 4
                notification_period: 5
                check_interval: 6
                retry_interval: 7

        '''
        self.run_config_gen(input_yaml)
        self.assertEquals(self.host_definition.get("host_name"), "testhost01")
        self.assertEquals(self.host_definition.get("max_check_attempts"), 5)
        # these values used to be removed from the host definition in the version for the old format
        # but the new version no longer exhibits this behavior
        self.assertEquals(self.host_definition.get("hostgroup_name"), "group name")
        self.assertEquals(self.host_definition.get("service_description"), "desc of service")
        self.assertEquals(self.host_definition.get("is_volatile"), 1)

    def test_that_for_yaml_config_without_host_section_a_minimal_host_definition_is_generated(self):
        input_yaml = '''
            defaults:
                    host_name: testhost01
                    check_period: 2
                    max_check_attempts: 3
                    notification_interval: 4
                    notification_period: 5
                    check_interval: 6
                    retry_interval: 7

            services:
                s1:
                    service_description: 234
                    check_command: check_graphite_disk_usage!_boot!90!95
        '''
        hostname = "testhost01"
        self.run_config_gen(input_yaml)
        # there is no hostname but the values should still be added through the defaults
        self.assertTrue("host_name" in self.host_definition.keys())

    def test_generates_check_definition(self):
        input_yaml = '''
            services:
                s1:
                    check_command: check_graphite_disk_usage!_boot!90!95
                    service_description: service 1
            defaults:
                check_command: check_graphite_disk_usage!_data!90!95
                check_period: workhours
                host_name: testhost01
                max_check_attempts: 3
                notification_interval: 4
                notification_period: 5
                check_interval: 6
                retry_interval: 7
        '''
        hostname = "testhost01"
        self.run_config_gen(input_yaml)
        self.assertEquals(len(self.service_definitions), 1)
        self.assertEquals(self.service_definitions[0].get("host_name"), hostname)
        self.assertEquals(self.service_definitions[0].get("check_command"), "check_graphite_disk_usage!_boot!90!95")
        self.assertEquals(self.service_definitions[0].get("check_period"), "workhours")

    def test_that_defaults_are_used_for_generation_of_service_definition(self):
        input_yaml = '''
            defaults:
                check_period:   24x7
                max_check_attempts:    5
                host_name: testhost01
                notification_interval: 4
                notification_period: 5
                check_interval: 6
                retry_interval: 7

            services:
                s1:
                  service_description: service1
                  check_command: commando
        '''
        
        hostname = "testhost01"
        self.run_config_gen(input_yaml)
        self.assertEquals(self.service_definitions[0].get("host_name"), hostname)
        self.assertEquals(self.service_definitions[0].get("check_command"), "commando")
        self.assertEquals(self.service_definitions[0].get("check_period"), "24x7")
        self.assertEquals(self.service_definitions[0].get("max_check_attempts"), 5)

    def test_that_service_id_is_set(self):
        input_yaml = '''
            defaults:
                check_period:   24x7
                host_name:    foobar
                max_check_attempts: 1
                notification_interval: 1
                notification_period: no_idea

            services:
                s1:
                  service_description: service1
                  check_command: commando
        '''
        
        hostname = "testhost01"
        self.run_config_gen(input_yaml)
        self.assertEquals(self.service_definitions[0].get("_service_id"), "s1")

    def test_that_host_only_defaults_are_no_longer_supported(self):
        """the old version automatically removed some directives that only applied to hosts from services
        this behavior is no longer supported
        """
        input_yaml = '''
            defaults:
                alias:    hostnamealias
                parents:    asdf
                vrml_image:    file
                statusmap_image:    file
                2d_coords:    x,y
                3d_coords:    x,y,z
                max_check_attempts:    5
                host_name: testhost01
                check_period: 2
                notification_interval: 4
                notification_period: 5
                check_interval: 6
                retry_interval: 7

            services:
                s1:
                  service_description: service 1
                  check_command: commando
        '''

        hostname = "testhost01"
        self.run_config_gen(input_yaml)
        self.assertEquals(self.service_definitions[0].get("host_name"), "testhost01")
        self.assertEquals(self.service_definitions[0].get("check_command"), "commando")
        self.assertEquals(self.service_definitions[0].get("max_check_attempts"), 5)
        self.assertEquals(self.service_definitions[0].get("alias"), "hostnamealias")
        self.assertEquals(self.service_definitions[0].get("parents"), "asdf")
        self.assertEquals(self.service_definitions[0].get("vrml_image"), "file")
        self.assertEquals(self.service_definitions[0].get("statusmap_image"), "file")
        self.assertEquals(self.service_definitions[0].get("2d_coords"), "x,y")
        self.assertEquals(self.service_definitions[0].get("3d_coords"), "x,y,z")

    def test_error_on_unsupported_section(self):
        """if the input-YAML contains a non-supported section, an exception should be thrown"""
        input_yaml = '''
            defaults:
                whatever: whatever
            services:
                - check_command: commando
            unsupported:
                - whatever
        '''
        hostname = "testhost01"
        self.assertRaises(UnknownSectionException, self.run_config_gen, input_yaml)


    def test_error_on_missing_hostname_in_service(self):
        """if the generated output contains a service section with no host_name, an exception should be thrown"""
        input_yaml = '''
            services:
                s1:
                   check_command: commando
        '''
        hostname = "testhost01"
        self.assertRaises(MandatoryDirectiveMissingException, self.run_config_gen, input_yaml)

    def test_error_on_missing_hostname_in_host(self):
        """if the generated output contains a service section with no host_name, an exception should be thrown"""
        input_yaml = '''
            host:
                a: b
        '''
        hostname = "testhost01"
        self.assertRaises(MandatoryDirectiveMissingException, self.run_config_gen, input_yaml)

    def test_error_on_different_hostnames_in_sections(self):
        """if the generated output contains a service section with no host_name, an exception should be thrown"""
        input_yaml = '''
            defaults:
                max_check_attempts:    5
                check_period: 2
                notification_interval: 4
                notification_period: 5
                check_interval: 6
                retry_interval: 7
            host:
                host_name: testhost01

            services:
                s1:
                   service_description: service 1
                   check_command: cmd1
                   host_name: testhost01
                s2:
                   service_description: service 2
                   check_command: cmd2
                   host_name: testhost02
        '''
        hostname = "testhost01"
        self.assertRaises(HostNamesNotEqualException, self.run_config_gen, input_yaml)


    def test_error_section_descriptions_not_unique(self):
        """if the generated output contains a service section with no host_name, an exception should be thrown"""
        input_yaml = '''
            defaults:
                max_check_attempts:    5
                check_period: 2
                notification_interval: 4
                notification_period: 5
                check_interval: 6
                retry_interval: 7
            host:
                host_name: testhost01

            services:
                s1:
                   service_description: service 1
                   check_command: cmd1
                   host_name: testhost01
                s2:
                   service_description: service 1
                   check_command: cmd2
                   host_name: testhost01
        '''
        hostname = "testhost01"
        self.assertRaises(ServiceDescriptionNotUniqueException, self.run_config_gen, input_yaml)

    def test_yaml_merger(self):
        input_dir = "itest_testhost07_multifile_dir"
        self.run_full_config_gen(input_dir, "testhost07.other.domain", "testhost07.other.domain.cfg")


if __name__ == "__main__":
    unittest.main()
