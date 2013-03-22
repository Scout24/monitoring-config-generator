import os
import yaml
import sys
import httplib2
import logging
import logging.handlers
from settings import CONFIG, CONFIG_FILE, read_config
from copy import deepcopy
import optparse
import re

class MonitoringConfigGenerator:

    def __init__(self,args = None):
        if args:
            if isinstance(args, basestring):
                args = [args]
        else:
            args= []
        self.logger = self.createLogger()

        usage = '''
%prog reads the yaml config of a host via file or http and generates nagios/icinga config from that
%prog [hostname|filename]

Configuration file can be specified in MONITORING_CONFIG_GENERATOR_CONFIG environment variable
'''
        parser = optparse.OptionParser(usage=usage, prog="monitoring_config_generator")
        parser.add_option("--debug", dest="debug", action="store_true", default=False, help="Enable debug logging [%default]")
        parser.add_option("--targetdir", dest="targetDir", action="store", default=CONFIG['TARGET_DIR'], type="string", help="Directory for generated config files")
        self.options, self.args = parser.parse_args(args) 
        if self.options.debug:
            loghandler = logging.StreamHandler()
            loghandler.setFormatter(logging.Formatter('yaml_server[%(filename)s:%(lineno)d]: %(levelname)s: %(message)s'))
            self.logger.addHandler(loghandler)
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug("Debug logging enabled via command line")

        self.targetDir = self.options.targetDir
        if not os.path.isdir(self.targetDir):
            raise BaseException("%s is not a directory" % self.targetDir)
        self.logger.debug("Using %s as target dir" % self.targetDir) 
        
        if len(self.args) < 1:
            self.logger.fatal("Need to get at least one host to operate on")
            raise BaseException("Need to get at least one host to operate on")
        self.logger.debug("Args: %s" % self.args)
        


    def createLogger(self):
        logger = logging.getLogger()
        if len(logger.handlers) == 0:
            loghandler = logging.handlers.SysLogHandler(address='/dev/log')
            loghandler.setFormatter(logging.Formatter('monitoring_config_generator[' + str(os.getpid()) + ']: %(levelname)s: %(message)s'))
            logger.addHandler(loghandler)
        logger.setLevel(logging.INFO)
        return logger

    def generate(self):
        argument = self.args[0]
        if os.path.isfile(argument):
            (hostname,ext) = os.path.splitext(os.path.basename(argument))
            self.logger.debug("Reading from %s for %s" % (argument,hostname))
            yamlconfig = self.readYamlFromFile(argument)
        else:
            hostname = argument
            yamlconfig = self.readYamlConfigFromWebserver(hostname)            

        if len(yamlconfig) == 0:
            return 1
            
        icingaConfig = self.generateIcingaConfig(hostname, yamlconfig)
        outputPath = os.path.join(self.options.targetDir, hostname + '.cfg')
        self.dumpIcingaConfig(icingaConfig, outputPath)
        return 0
        
    def readYamlConfigFromWebserver(self, hostname):
        h = httplib2.Http()
        url = "http://" + hostname + ":" + CONFIG['PORT'] + CONFIG['RESOURCE']
        self.logger.debug("Retrieving config from URL: %s" % url)
        
        resp = {}
        try:
            resp, content = h.request(url, "GET")
        except Exception:
            self.logger.warn("Problem retrieving config for %s from %s" % (hostname, url))
            return ""
        else:
            if resp['status'] == '200':
                return yaml.load(content)
            
        self.logger.debug("Host %s returned with %s." % (hostname, resp['status']))
        return ""
        
    def readYamlFromFile(self, filepath):
        with open(filepath, 'r') as f:
            content = f.read()
            return yaml.load(content)

    def generateIcingaConfig(self, hostname, yamlConfig):
        icingaConfig = dict()
        icingaConfig['host'] = self.generateHostDefinition(hostname, yamlConfig)
        icingaConfig['services'] = self.generateServiceDefinitions(hostname, yamlConfig)
        return icingaConfig

    def dumpIcingaConfig(self, rawConfig, outputPath):
        icinga = [{
            "host" : rawConfig.get("host", {})
        }]
        for service in rawConfig.get("services", []):
            icinga.append({"service": service})
        
        indent = CONFIG['INDENT']
        
        with open(outputPath, 'w') as f:
            for section in icinga:
                for (sectionType, sectionData) in section.items():
                    if sectionData:
                        f.write("define %s {\n%s\n}\n\n" % (sectionType, "\n".join([indent + "%-45s%s" % item for item in sectionData.items()])))
            f.close()
        self.logger.debug("Created %s" % outputPath)
        
        
    def generateHostDefinition(self, hostname, yamlConfig):
        hostDefinition = {}
        hostDefinition = self.fillWithDefaults(yamlConfig, hostDefinition)
        self.removeEntriesFromDict(hostDefinition, CONFIG['SERVICE_ONLY_DIRECTIVES'])        

        if 'host' in yamlConfig:
            hostDefinition.update(deepcopy(yamlConfig['host']))
            
        hostDefinition['address'] = hostname
        hostDefinition['alias'] = hostname
        hostDefinition['host_name'] = self.extractHostnameFromFqdn(hostname)
        return hostDefinition
            
    def generateServiceDefinitions(self, hostname, yamlConfig):
        serviceDefinitions = []
        servicesConfig = {}

        if 'services' in yamlConfig:        
            servicesConfig = yamlConfig.get("services", {})
        elif 'checks' in yamlConfig:
            servicesConfig = yamlConfig.get("checks", {})
            self.logger.warn("Host: %s is still using the old yaml format with checks syntax." % hostname)
        
            
        for serviceConfig in servicesConfig:
            serviceDefinitions.append(self.generateServiceDefinition(hostname, yamlConfig, serviceConfig))
            
        return serviceDefinitions

    def generateServiceDefinition(self, hostname, yamlConfig, serviceConfig):
        serviceDefinition = {}
        serviceDefinition = self.fillWithDefaults(yamlConfig, serviceDefinition)
        self.removeEntriesFromDict(serviceDefinition, CONFIG['HOST_ONLY_DIRECTIVES'])
        serviceDefinition.update(deepcopy(serviceConfig))

        if 'type' in serviceDefinition:
            self.removeEntriesFromDict(serviceDefinition, ['type'])
            self.logger.warn("Host: %s is still using the old yaml format with type elements in checks." % hostname)
            
        serviceDefinition["host_name"] = self.extractHostnameFromFqdn(hostname)
        return serviceDefinition
    
    
    def fillWithDefaults(self, config, definition):
        if 'defaults' in config:
            definition = deepcopy(config['defaults'])
        return definition
        

    def fillPlaceholdersInCommand(self, command, config):
        for attr in config:
            repl = "${" + attr + "}"
            if repl in command:
                command = command.replace(repl, str(config[attr]))

        return command

    def removeEntriesFromDict(self, dict, keys):
        for key in keys:
            if key in dict:
                del dict[key]
                
    def extractHostnameFromFqdn(self, hostname):
        if '.' in hostname:
            hostname = hostname.split('.')[0]
        return hostname

def mainMethod():
    try:
        sys.exit(MonitoringConfigGenerator(sys.argv[1:]).generate())
    except SystemExit:
        pass
    except BaseException as e:
        print >> sys.stderr,"ERROR: " + str(e)
        sys.exit(1)

if __name__ == '__main__':
    mainMethod()
