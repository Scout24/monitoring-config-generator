import os
import unittest

from TestLogger import init_test_logger

os.environ['MONITORING_CONFIG_GENERATOR_CONFIG'] = "testdata/testconfig.yaml"
from monitoring_config_generator.MonitoringConfigGenerator import InputReader


class Test(unittest.TestCase):

    init_test_logger()

    def test_etag_no_input(self):
        input_reader = InputReader("test.some.domain.yaml", "testDirName")
        input_reader.read_input()
        self.assertEquals(None, input_reader.etag)

    def test_read_file(self):
        host_name = "testhost03.other.domain"
        yaml_filename = host_name + ".yaml"
        cfg_filename = host_name + ".cfg"
        input_dir = "testdata/itest_testhost03_new_format"
        full_input_path = os.path.join(input_dir, yaml_filename)
        output_dir = "testOutputDir"
        full_output_path = os.path.join(output_dir, cfg_filename)
        input_reader = InputReader(full_input_path, output_dir)
        input_reader.read_input()
        self.assertEquals(host_name, input_reader.hostname)
        self.assertEquals(full_input_path, input_reader.filename)
        self.assertEquals(full_output_path, input_reader.output_path)
        self.assertTrue(input_reader.config_changed)
        self.assertTrue(input_reader.is_file)

        # output dir doesn't exist, so there should be no etag
        self.assertEquals(None, input_reader.etag)
