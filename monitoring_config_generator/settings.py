import os
import sys
import yaml


# for local testing use MONITORING_CONFIG_GENERATOR_CONFIG=../testdata/testconfig.yaml 

# ica servers
DEF_CONFIG = {
                'TARGET_DIR' : '/etc/icinga/conf.d/generated',
                'INDENT' : '        ',
                'META_KEYS' : [],
                'PORT' : "8935",
                'RESOURCE' : "/monitoring",
               }

CONFIG_FILE = '/etc/monitoring_config_generator/config.yaml'
# get config file
if 'MONITORING_CONFIG_GENERATOR_CONFIG' in os.environ and len(os.environ['MONITORING_CONFIG_GENERATOR_CONFIG']) > 0:
    CONFIG_FILE = os.environ['MONITORING_CONFIG_GENERATOR_CONFIG']
    print 'Config file overridden in environment to: ' + CONFIG_FILE


# directives in Icinga host- and service-definitions are mandatory, MonitoringConfigGenerator will check that
# the generated config contains all directives
ICINGA_HOST_DIRECTIVES = ["host_name",
                          # "alias",
                          "max_check_attempts",
                          "check_period",
                          "notification_interval",
                          "notification_period"]

ICINGA_SERVICE_DIRECTIVES = ["host_name",
                             "service_description",
                             "check_command",
                             "max_check_attempts",
#                             "check_interval",
#                             "retry_interval",
                             "check_period",
                             "notification_interval",
                             "notification_period"]

def read_config(cfile=CONFIG_FILE):
    # merge defaults with config from config file
    if os.path.exists(cfile):
        print 'reading config from %s' % cfile
        config_file = open(cfile)
        new_config = yaml.load(config_file)
        config_file.close()
        CONFIG = dict(DEF_CONFIG.items() + new_config.items())
    else:
        print >>sys.stderr, 'config %s not found' % cfile
        CONFIG = DEF_CONFIG
    return CONFIG

CONFIG = read_config()