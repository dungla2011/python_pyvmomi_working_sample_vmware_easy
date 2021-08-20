import os
from pprint import pp

import requests
import urllib3

import sys

from com.vmware.vcenter.vm.hardware_client import Memory
from samples.vsphere.vcenter.helper.vm_helper import get_vm

sys.path.append(os.path.realpath(".") + '/venv/Lib/site-packages/')

from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
from tools import cli, pchelper, service_instance

from vmware.vapi.vsphere.client import create_vsphere_client

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


session = requests.session()

# Disable cert verification for demo purpose.
# This is not recommended in a production environment.
session.verify = False

# Disable the secure connection warning for demo purpose.
# This is not recommended in a production environment.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Connect to a vCenter Server using username and password
vsphere_client = create_vsphere_client(server=serverDomain, username=username, password=password, session=session)


vm_name = "2012-temp-12.8.21"

vm = get_vm(vsphere_client, vm_name)

if not vm:
    raise Exception('Sample requires an existing vm with name ({}). '
                    'Please create the vm first.'.format(vm_name))

print("Using VM '{}' ({}) for Memory Sample".format(vm_name, vm))

print('\n# Example: Get current Memory configuration')
memory_info = vsphere_client.vcenter.vm.hardware.Memory.get(vm)
print('vm.hardware.Memory.get({}) -> {}'.format(vm, pp(memory_info)))

print('\n# Example: Update memory size_mib field of Memory configuration')
update_spec = Memory.UpdateSpec(size_mib=2 * 1024)
print('vm.hardware.Memory.update({}, {})'.format(vm, update_spec))

vsphere_client.vcenter.vm.hardware.Memory.update(vm, update_spec)


