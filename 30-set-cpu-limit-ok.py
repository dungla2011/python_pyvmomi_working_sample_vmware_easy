#----------------- Start of code capture -----------------
import os
import sys
sys.path.append(os.path.realpath(".") + '/venv/Lib/site-packages/')


from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
from tools import cli, pchelper, service_instance


from configparser import ConfigParser
config = ConfigParser()
# read user/pw from ini
fileConf = '../vc_info.ini'  # File config store login info, see vc_info.ini.sample
# If file config exists:
if os.path.exists(fileConf):
    config.read(fileConf)

    serverDomain = config.get('config', 'server')
    username = config.get('config', 'username')
    password = config.get('config', 'password')
else:
    serverDomain = "<enter your server domain>"
    username = "<enter user, ex: administrator@vsphere.local>"
    password = "<enter password>"
###############################



vm_name = "2012-test1-2020"
#---------------ReconfigVM_Task---------------
spec = vim.vm.ConfigSpec()
spec.cpuAllocation = vim.ResourceAllocationInfo()
spec.cpuAllocation.limit = 2200 #mhz
spec.deviceChange = []
spec.cpuFeatureMask = []

si = SmartConnect(host=serverDomain,
                                user=username,
                                pwd=password,
                                port=443,disableSslCertValidation=True)

content = si.RetrieveContent()
vm = pchelper.get_obj(content, [vim.VirtualMachine], vm_name)
vm.ReconfigVM_Task(spec)
