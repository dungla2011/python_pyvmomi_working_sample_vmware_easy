import os

import requests
import urllib3

import sys
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

# List all VMs inside the vCenter Server
ret = vsphere_client.vcenter.VM.list()

si = SmartConnect(host=serverDomain,
                                user=username,
                                pwd=password,
                                port=443,disableSslCertValidation=True)

content = si.RetrieveContent()

# search_index = si.content.searchIndex
#
# print(vars(search_index))
#
# quit()



for ob in ret:
    # ob.vm
    if 'win2012-test1_2021' in ob.name:
        print(ob.vm, '- ', ob.name)
        # vm = search_index.FindByUuid(None, ob.vm, True)
        vm = pchelper.get_obj(content, [vim.VirtualMachine], ob.name)
        var = vars(vm)
        # print(" OBJ TYPE = ", type(var))
        print(" vmid = ", var['_moId'])
        vmid = var['_moId']

        if vmid == ob.vm:
            input("...before config ...")
            print(" OK FOUND: " + vmid)
            #---------------ReconfigVM_Task---------------
            spec = vim.vm.ConfigSpec()
            spec.cpuAllocation = vim.ResourceAllocationInfo()
            spec.cpuAllocation.limit = 2200 #mhz
            spec.deviceChange = []
            spec.cpuFeatureMask = []
            vm.ReconfigVM_Task(spec)
            input("...done config ...")

