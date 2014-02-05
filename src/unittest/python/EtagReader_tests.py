import os
import unittest

os.environ['MONITORING_CONFIG_GENERATOR_CONFIG'] = "testdata/testconfig.yaml"
from monitoring_config_generator.readers import ETagReader


class Test(unittest.TestCase):

    def test_reads_etag_from_file(self):
        self.assertEquals("754d61019fb8a470a654c25e59b10311963f00b5e2d2784712732feed6a82066",
                          ETagReader("testdata/etag/testhost01.some.domain.etag.cfg").etag)

    def test_file_exists_but_null_etag(self):
        self.assertEquals(None, ETagReader("testdata/etag/testhost01.some.domain.nulletag.cfg").etag)

    def test_file_exists_but_no_etag(self):
        self.assertEquals(None, ETagReader("testdata/etag/testhost01.some.domain.noetag.cfg").etag)

    def test_file_does_not_exist(self):
        self.assertEquals(None, ETagReader("idontex.st").etag)
