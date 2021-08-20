

import os
from pprint import pp

import requests
import urllib3

import sys

from com.vmware.vcenter.vm.hardware_client import Memory
from com.vmware.vcenter.vm_client import Power
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

session.verify = False

# Disable the secure connection warning for demo purpose.
# This is not recommended in a production environment.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Connect to a vCenter Server using username and password
vsphere_client = create_vsphere_client(server=serverDomain, username=username, password=password, session=session)

# List all VMs inside the vCenter Server
ret = vsphere_client.vcenter.VM.list()


for ob in ret:

    # ob.vm
    if 'win2012-mrlinh_2021-08' in ob.name:
        vmid = ob.vm

        print("Using VM '{}' ({}) for Memory Sample".format(ob.name, vmid))

        input("...1")

        print('\n# Example: Get current Memory configuration')
        memory_info = vsphere_client.vcenter.vm.hardware.Memory.get(vmid)
        print('vm.hardware.Memory.get({}) -> {}'.format(vmid, pp(memory_info)))

        if memory_info.size_mib == 2 * 1024:
            print(" 2048 OK, so ignore ")
            continue

        print('\n# Example: Update memory size_mib field of Memory configuration')
        update_spec = Memory.UpdateSpec(size_mib=2 * 1024)
        print('vm.hardware.Memory.update({}, {})'.format(vmid, update_spec))

        print('\n# Get current vm power state')
        status = vsphere_client.vcenter.vm.Power.get(vmid)
        print('vm.Power.get({}) -> {}'.format(vmid, pp(status)))


        if status == Power.Info(state=Power.State.POWERED_ON):
            input(" Any key to power off : ...")
            print('\n# Example: VM is powered on, power it off')
            vsphere_client.vcenter.vm.Power.stop(vmid)
            print('vm.Power.stop({})'.format(vmid))

        vsphere_client.vcenter.vm.hardware.Memory.update(vmid, update_spec)

        # Power on the vm
        print('# Example: Power on the vm')
        vsphere_client.vcenter.vm.Power.start(vmid)
        print('vm.Power.start({})'.format(vmid))

        input("...Done ")