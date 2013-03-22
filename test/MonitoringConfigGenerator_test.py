import unittest
import os,shutil,logging
# load test configuration
os.environ['MONITORING_CONFIG_GENERATOR_CONFIG']="testdata/testconfig.yaml"
from monitoring_config_generator.settings import CONFIG
from monitoring_config_generator.MonitoringConfigGenerator import MonitoringConfigGenerator

import yaml

class Test(unittest.TestCase):

    testDir = "testdata"
    shutil.rmtree(CONFIG["TARGET_DIR"], True)
    os.mkdir(CONFIG["TARGET_DIR"])
    
    # set up logging without syslog
    logger = logging.getLogger()
    loghandler = logging.StreamHandler()
    loghandler.setFormatter(logging.Formatter('yaml_server[%(filename)s:%(lineno)d]: %(levelname)s: %(message)s'))
    logger.addHandler(loghandler)
    logger.setLevel(logging.DEBUG)

    def testGeneratesConfigFromFile(self):
        thisTestDir = os.path.join(self.testDir, "itest_testhost02")
        inputPath = os.path.abspath(os.path.join(thisTestDir, "testhost02.other.domain.yaml"))
        MonitoringConfigGenerator(inputPath).generate()

        outputPath = os.path.join(CONFIG['TARGET_DIR'], 'testhost02.other.domain.cfg')
        expectedOutputPath = os.path.join(thisTestDir, 'testhost02.other.domain.cfg')

        self.assertThatContentsOfFilesIsIdentical(outputPath, expectedOutputPath)
    
    def testGeneratesConfigFromFileWithOldYamlFormat(self):
        thisTestDir = os.path.join(self.testDir, "itest_testhost01_old_format")
        inputPath = os.path.abspath(os.path.join(thisTestDir, "testhost01.some.domain.yaml"))
        MonitoringConfigGenerator(inputPath).generate()

        outputPath = os.path.join(CONFIG['TARGET_DIR'], 'testhost01.some.domain.cfg')
        expectedOutputPath = os.path.join(thisTestDir, 'testhost01.some.domain.cfg')

        self.assertThatContentsOfFilesIsIdentical(outputPath, expectedOutputPath)
        
    def assertThatContentsOfFilesIsIdentical(self, file1, file2):
        with open(file1, 'r') as actualFile:
            with open(file2, 'r') as expectedFile:
                linecount=0
                for expectedLine in expectedFile:
                    linecount+=1
                    actualLine = actualFile.readline()
                    self.assertEquals(actualLine, expectedLine,"Line %i differs" % linecount)


    def testGeneratesIcingaConfig(self):
        inputYaml = '''
            host:
                address: testhost01.some.domain
            checks:
                -  check_command: check_graphite_disk_usage!_boot!90!95
        '''
        yamlConfig = yaml.load(inputYaml)
        icingaConfig = MonitoringConfigGenerator("testhost01").generateIcingaConfig("testhost01", yamlConfig)
        self.assertTrue('host' in icingaConfig)
        self.assertTrue('services' in icingaConfig)

    def testGeneratesHostDefinition(self):
        inputYaml = '''
            host:
                check_period:   24x7
                max_check_attempts:    5
        '''
        
        yamlConfig = yaml.load(inputYaml)
        hostConfig = MonitoringConfigGenerator("testhost01.sub.domain").generateHostDefinition("testhost01.sub.domain", yamlConfig)
        self.assertEquals(hostConfig.get("address"), "testhost01.sub.domain")
        self.assertEquals(hostConfig.get("host_name"), "testhost01")
        self.assertEquals(hostConfig.get("check_period"), "24x7")
        self.assertEquals(hostConfig.get("max_check_attempts"), 5)
        
    def testThatDefaultsAreUsedForGenerationOfHostDefinition(self):
        inputYaml = '''
            defaults:
                check_period:   24x7
                max_check_attempts:    5
        '''
        
        yamlConfig = yaml.load(inputYaml)
        hostConfig = MonitoringConfigGenerator("testhost01.sub.domain").generateHostDefinition("testhost01.sub.domain", yamlConfig)
        self.assertEquals(hostConfig.get("address"), "testhost01.sub.domain")
        self.assertEquals(hostConfig.get("host_name"), "testhost01")
        self.assertEquals(hostConfig.get("check_period"), "24x7")
        self.assertEquals(hostConfig.get("max_check_attempts"), 5)
        
    def testThatServiceOnlyDefaultsAreNotUsedForGenerationOfHostDefinition(self):
        inputYaml = '''
            defaults:
                hostgroup_name:    group name
                service_description: desc of service
                is_volatile:    1
                max_check_attempts:    5
        '''
        
        yamlConfig = yaml.load(inputYaml)
        hostname = "testhost01.sub.domain"
        hostConfig = MonitoringConfigGenerator(hostname).generateHostDefinition(hostname, yamlConfig)
        self.assertEquals(hostConfig.get("host_name"), "testhost01")
        self.assertEquals(hostConfig.get("max_check_attempts"), 5)
        self.assertFalse("hostgroup_name" in hostConfig)    
        self.assertFalse("service_description" in hostConfig)        
        self.assertFalse("is_volatile" in hostConfig)    
        
        
    def testThatForYamlconfigWithoutHostSectionAMinimalHostdefinitionIsGenerated(self):
        yamlConfig = yaml.load("bla: ")
        hostConfig = MonitoringConfigGenerator("testhost01.sub.domain").generateHostDefinition("testhost01.sub.domain", yamlConfig)
        self.assertEquals(hostConfig.get("address"), "testhost01.sub.domain")
        self.assertEquals(hostConfig.get("host_name"), "testhost01")
        self.assertEquals(hostConfig.get("alias"), "testhost01.sub.domain")
        
        
        
    def testExtractsHostNameFromFqdn(self):
        fqdn = "testhost01.sub.domain"
        hostname = MonitoringConfigGenerator(fqdn).extractHostnameFromFqdn(fqdn)
        self.assertEquals(hostname, "testhost01")
        
    def testGeneratesCheckDefinition(self):
        inputYaml = '''
            checks:
                -   check_command: check_graphite_disk_usage!_boot!90!95
            defaults:
                check_command: check_graphite_disk_usage!_data!90!95
                check_period: workhours
        '''
        yamlConfig = yaml.load(inputYaml)
        hostname = "testhost01"
        checkConfig = MonitoringConfigGenerator(hostname).generateServiceDefinitions(hostname, yamlConfig)
        self.assertEquals(len(checkConfig), 1)
        self.assertEquals(checkConfig[0].get("host_name"), hostname)
        self.assertEquals(checkConfig[0].get("check_command"), "check_graphite_disk_usage!_boot!90!95")
        self.assertEquals(checkConfig[0].get("check_period"), "workhours")

    def testThatDefaultsAreUsedForGenerationOfServiceDefinition(self):
        inputYaml = '''
            defaults:
                check_period:   24x7
                max_check_attempts:    5
            
            checks:
                - check_command: commando
        '''
        
        yamlConfig = yaml.load(inputYaml)
        hostname = "testhost01"
        checkConfig = MonitoringConfigGenerator(hostname).generateServiceDefinitions(hostname, yamlConfig)
        self.assertEquals(checkConfig[0].get("host_name"), hostname)
        self.assertEquals(checkConfig[0].get("check_command"), "commando")
        self.assertEquals(checkConfig[0].get("check_period"), "24x7")
        self.assertEquals(checkConfig[0].get("max_check_attempts"), 5)
        
    def testThatHostOnlyDefaultsAreNotUsedForGenerationOfServiceDefinition(self):
        inputYaml = '''
            defaults:
                alias:    hostnamealias
                parents:    asdf
                vrml_image:    file
                statusmap_image:    file
                2d_coords:    x,y
                3d_coords:    x,y,z
                max_check_attempts:    5
            
            checks:
                - check_command: commando
        '''
        
        yamlConfig = yaml.load(inputYaml)
        hostname = "testhost01"
        checkConfig = MonitoringConfigGenerator(hostname).generateServiceDefinitions(hostname, yamlConfig)
        self.assertEquals(checkConfig[0].get("host_name"), hostname)
        self.assertEquals(checkConfig[0].get("check_command"), "commando")
        self.assertEquals(checkConfig[0].get("max_check_attempts"), 5)
        self.assertFalse("alias" in checkConfig[0])        
        self.assertFalse("parents" in checkConfig[0])        
        self.assertFalse("vrml_image" in checkConfig[0])        
        self.assertFalse("statusmap_image" in checkConfig[0])        
        self.assertFalse("2d_coords" in checkConfig[0])        
        self.assertFalse("3d_coords" in checkConfig[0])        

    def testRemovesEntriesFromDict(self):
        attributes = {'attr1': 'val1', 'attr2': 'val2', 'attr3': 'val3'}
        metaKeys = ['attr2', 'attr4']
        MonitoringConfigGenerator("test").removeEntriesFromDict(attributes, metaKeys)
        self.assertEqual(attributes, {'attr1': 'val1', 'attr3': 'val3'})
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()