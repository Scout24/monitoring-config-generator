
from pybuilder.core import use_plugin, init

use_plugin("python.core")
use_plugin("python.unittest")
use_plugin('python.install_dependencies')

name = "monitoring-config-generator"
default_task = "publish"



@init
def set_properties(project):
    project.depends_on('pyyaml')
    project.depends_on('httplib2')
