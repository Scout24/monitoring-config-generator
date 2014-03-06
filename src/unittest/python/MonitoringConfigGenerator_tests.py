import unittest
import os
import shutil

from mock import patch, Mock


os.environ['MONITORING_CONFIG_GENERATOR_CONFIG'] = "testdata/testconfig.yaml"
from monitoring_config_generator.settings import CONFIG
from monitoring_config_generator.yaml_tools.readers import Header
from monitoring_config_generator.MonitoringConfigGenerator import MonitoringConfigGenerator
from monitoring_config_generator.exceptions import *
from test_logger import init_test_logger


class TestMonitoringConfigGeneratorConstructor(unittest.TestCase):
    def test_init(self):
        target_uri = 'http://example.com:8935/monitoring'
        mcg = MonitoringConfigGenerator(url=target_uri)
        self.assertEquals(target_uri, mcg.source)

    @patch( 'monitoring_config_generator.MonitoringConfigGenerator.set_log_level_to_debug')
    def test_output_debug_log_to_console_called(self, set_level_to_debug_log):
        MonitoringConfigGenerator(url='http://example.com:8935/monitoring', debug_enabled=True)
        set_level_to_debug_log.assert_called_once_with()

    @patch('os.path.isdir')
    def test_target_dir_not_dir_raises_exception(self, mock_isdir):
        mock_isdir.return_value = False

        self.assertRaises(MonitoringConfigGeneratorException,
                          MonitoringConfigGenerator,
                          ['any_url', False, '/not_a_dir'])


class TestMonitoringConfigGeneratorGenerate(unittest.TestCase):
    @patch('monitoring_config_generator.MonitoringConfigGenerator.read_config')
    def test_empty_yaml_source_raises_syste_exit(self, read_config_mock):
        read_config_mock.return_value = (None, None)
        target_uri = 'http://example.com:8935/monitoring'
        mcg = MonitoringConfigGenerator(target_uri)
        self.assertRaises(SystemExit, mcg.generate)

    @patch('monitoring_config_generator.MonitoringConfigGenerator.YamlConfig')
    @patch('monitoring_config_generator.MonitoringConfigGenerator.read_config')
    def test_unexpanded_variables_raises_an_error(self, read_config_mock, yaml_config_mock):
        read_config_mock.return_value = (True, True)
        yaml_config_mock.side_effect = ConfigurationContainsUndefinedVariables
        target_uri = 'http://example.com:8935/monitoring'
        mcg = MonitoringConfigGenerator(target_uri)
        self.assertRaises(ConfigurationContainsUndefinedVariables, mcg.generate)

    @patch('monitoring_config_generator.MonitoringConfigGenerator.YamlConfig')
    @patch('monitoring_config_generator.MonitoringConfigGenerator.read_config')
    def test_missing_hostname_raises_an_error(self, read_config_mock, yaml_config_mock):
        read_config_mock.return_value = (True, True)
        yaml_config_mock.return_value = Mock(host_name=None)
        target_uri = 'http://example.com:8935/monitoring'
        mcg = MonitoringConfigGenerator(target_uri)
        self.assertRaises(NoSuchHostname, mcg.generate)

    @patch('monitoring_config_generator.MonitoringConfigGenerator.YamlConfig')
    @patch('monitoring_config_generator.MonitoringConfigGenerator.YamlToIcinga')
    @patch('monitoring_config_generator.MonitoringConfigGenerator.read_config')
    @patch('monitoring_config_generator.MonitoringConfigGenerator.MonitoringConfigGenerator.write_output')
    @patch('monitoring_config_generator.MonitoringConfigGenerator.MonitoringConfigGenerator._is_newer')
    def test_return_the_file_name_if_the_config_changed(self,
                                                        is_newer_mock,
                                                        write_output_mock,
                                                        read_config_mock,
                                                        yaml_to_icinga_mock,
                                                        yaml_config_mock):
        read_config_mock.return_value = ({'host': None, 'services': None}, Header())
        is_newer_mock.return_value = True
        yaml_instance_mock = Mock()
        yaml_config_mock.return_value = yaml_instance_mock
        yaml_instance_mock.host = 'any_host_section'
        yaml_instance_mock.host_name = 'any_hostname'

        mcg = MonitoringConfigGenerator('http://example.com:8935/monitoring')

        self.assertEquals('any_hostname.cfg', mcg.generate())

    @patch('monitoring_config_generator.MonitoringConfigGenerator.YamlConfig')
    @patch('monitoring_config_generator.MonitoringConfigGenerator.YamlToIcinga')
    @patch('monitoring_config_generator.MonitoringConfigGenerator.read_config')
    @patch('monitoring_config_generator.MonitoringConfigGenerator.MonitoringConfigGenerator.write_output')
    @patch('monitoring_config_generator.MonitoringConfigGenerator.MonitoringConfigGenerator._is_newer')
    def test_returns_none_if_the_config_did_not_change(self,
                                                       is_newer_mock,
                                                       write_output_mock,
                                                       read_config_mock,
                                                       yaml_to_icinga_mock,
                                                       yaml_config_mock):
        read_config_mock.return_value = ({'host': None, 'services': None}, Header())
        is_newer_mock.return_value = False
        yaml_instance_mock = Mock()
        yaml_config_mock.return_value = yaml_instance_mock
        yaml_instance_mock.host = 'any_host_section'
        yaml_instance_mock.host_name = 'any_hostname'

        mcg = MonitoringConfigGenerator('http://example.com:8935/monitoring')

        self.assertEquals(None, mcg.generate())

    @patch('monitoring_config_generator.MonitoringConfigGenerator.YamlConfig')
    @patch('monitoring_config_generator.MonitoringConfigGenerator.YamlToIcinga')
    @patch('monitoring_config_generator.MonitoringConfigGenerator.read_config')
    @patch('monitoring_config_generator.MonitoringConfigGenerator.MonitoringConfigGenerator.write_output')
    @patch('monitoring_config_generator.MonitoringConfigGenerator.MonitoringConfigGenerator._is_newer')
    def test_returns_none_if_the_config_did_not_change(self,
                                                       is_newer_mock,
                                                       write_output_mock,
                                                       read_config_mock,
                                                       yaml_to_icinga_mock,
                                                       yaml_config_mock):
        read_config_mock.return_value = ({'host': None, 'services': None}, Header())
        is_newer_mock.return_value = True
        yaml_instance_mock = Mock()
        yaml_config_mock.return_value = yaml_instance_mock
        yaml_instance_mock.host = None
        yaml_instance_mock.host_name = 'any_hostname'

        mcg = MonitoringConfigGenerator('http://example.com:8935/monitoring')

        self.assertEquals(None, mcg.generate())


class Test(unittest.TestCase):
    def setUp(self):
        self.testDir = "testdata"
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
            self.assertFalse("${" in line, "found undefined variable in " + filename)

    def get_yaml_file_from_directory(self, directory):
        input_directory = os.path.join(self.testDir, directory)
        all_yaml = [filename for filename in os.listdir(input_directory) if filename.endswith(".yaml")]
        self.assertEquals(1, len(all_yaml))
        yaml_file = all_yaml[0]
        yaml_file_with_path = os.path.abspath(os.path.join(input_directory, yaml_file))
        return yaml_file_with_path

    def run_config_generator_for_invalid_file(self, input_dir, generated_configuration_filename):
        yaml_file = self.get_yaml_file_from_directory(input_dir)
        MonitoringConfigGenerator(yaml_file).generate()
        output_path = os.path.join(CONFIG['TARGET_DIR'], generated_configuration_filename)
        self.assertFalse(os.path.exists(output_path), "Generator generated file for undefined variables")

    def test_generated_config_with_missing__variable(self):
        yaml_source = self.get_yaml_file_from_directory("itest_testhost08_variables")
        config_generator = MonitoringConfigGenerator(yaml_source)
        self.assertRaises(ConfigurationContainsUndefinedVariables, config_generator.generate)

    def test_generated_config_with_missing_service_variable(self):
        yaml_source = self.get_yaml_file_from_directory("itest_testhost09_variables")
        config_generator = MonitoringConfigGenerator(yaml_source)
        self.assertRaises(ConfigurationContainsUndefinedVariables, config_generator.generate)

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

    @patch('os.path.getmtime')
    def mtime_helper(self, side_effect, correct, getmtime_mock):
        getmtime_mock.side_effect = side_effect
        input_directory = os.path.join(self.testDir, 'itest_testservice')
        yaml1 = os.path.join(input_directory, 'testhost1.yaml')
        MonitoringConfigGenerator(yaml1).generate()
        yaml2 = os.path.join(input_directory, 'testhost2.yaml')
        MonitoringConfigGenerator(yaml2).generate()
        received = os.path.join(CONFIG['TARGET_DIR'], 'servicetest.cfg')
        expected = os.path.join(input_directory, 'config_from_testhost%d.cfg' %
                                                 correct)
        self.assert_that_contents_of_files_is_identical(expected, received)

    def test_service_respects_mtime_with_older_file(self):
        # make the first file who's mtime we read appear older
        self.mtime_helper([1, 0], 1)

    def test_service_respects_mtime_with_newer_file(self):
        # now reverse file who's mtime we read appear older
        self.mtime_helper([0, 1], 2)

    def assert_that_contents_of_files_is_identical(self, actual_file_name, expected_file_name):
        lines_actual = open(actual_file_name, 'r').readlines()
        lines_expected = open(expected_file_name, 'r').readlines()
        len_actual = len(lines_actual)
        len_expected = len(lines_expected)

        self.assertEquals(len_actual,
                          len_expected,
                          "number of lines not equal (expected=%s, actual=%s)" % (len_expected, len_actual))

        for index in range(len_expected):
            lineActual = lines_actual[index]
            lineExpected = lines_expected[index]

            # special handling for the the header line
            # because "Created by ... " contains a date, so it will not match exactly
            if lineExpected.startswith(Header.MON_CONF_GEN_COMMENT):
                # so if it is the line containing the date we will only compare the start of the line
                self.assertTrue(lineActual.startswith(Header.MON_CONF_GEN_COMMENT))
            elif lineExpected.startswith(Header.MTIME_COMMMENT):
                self.assertTrue(lineActual.startswith(Header.MTIME_COMMMENT))
            else:
                # other lines will be compared completely of course
                self.assertEquals(lineActual,
                                  lineExpected,
                                  "Line #%d does not match (expected='%s', actual='%s'" %
                                  (index, lineExpected, lineActual))


    def test_yaml_merger(self):
        input_dir = "itest_testhost07_multifile_dir"
        self.run_full_config_gen(input_dir, "testhost07", "testhost07.cfg")


if __name__ == "__main__":
    unittest.main()
