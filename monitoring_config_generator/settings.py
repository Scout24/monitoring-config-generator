import os,sys,yaml


# for local testing use MONITORING_CONFIG_GENERATOR_CONFIG=../testdata/testconfig.yaml 

# ica servers
DEF_CONFIG = {
                'TARGET_DIR' : '/etc/icinga/conf.d/generated',
                'INDENT' : '        ',
                'META_KEYS' : [],
                'PORT' : "8935",
                'RESOURCE' : "/monitoring",
                'HOST_ONLY_DIRECTIVES': ['alias', 'parents', 'vrml_image', 'statusmap_image', '2d_coords', '3d_coords'],
                'SERVICE_ONLY_DIRECTIVES': ['hostgroup_name', 'service_description', 'is_volatile'],
               }

CONFIG_FILE = '/etc/monitoring_config_generator/config.yaml'
# get config file
if 'MONITORING_CONFIG_GENERATOR_CONFIG' in os.environ and len(os.environ['MONITORING_CONFIG_GENERATOR_CONFIG']) > 0:
    CONFIG_FILE = os.environ['MONITORING_CONFIG_GENERATOR_CONFIG']
    print 'Config file overridden in environment to: '+CONFIG_FILE

    

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