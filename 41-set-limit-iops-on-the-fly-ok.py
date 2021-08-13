#----------------- Start of code capture -----------------
import os

import sys
sys.path.append(os.path.realpath(".") + '/venv/Lib/site-packages/')


from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
from tools import cli, pchelper, service_instance
from pprint import pprint


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


vm_name = "_W10-for-test-network-s1-121.x"

si = SmartConnect(host=serverDomain,
                                user=username,
                                pwd=password,
                                port=443,disableSslCertValidation=True)

content = si.RetrieveContent()

# print(content)

virtual_machine = pchelper.get_obj(content, [vim.VirtualMachine], vm_name)
# if vmuuid:
#     search_index = si.content.searchIndex
#     vm = search_index.FindByUuid(None, vmuuid, True)
# elif vm_name:
#     content = si.RetrieveContent()
#     vm = pchelper.get_obj(content, [vim.VirtualMachine], vm_name)


summary = virtual_machine.summary

print("\n")
print("------------------------")
print(summary)
print("VID       : ", summary.vm)
print("Name       : ", summary.config)
print("Name       : ", summary.config.name)
print("memorySizeMB       : ", summary.config.memorySizeMB)

print("=== Disk Info       : ")

info = virtual_machine.config.hardware.device
for each in info:
    if "VirtualDisk" in type(each).__name__:
        print("-----: " + type(each).__name__)
        each.storageIOAllocation.limit = 1001
        # print(each)
        spec = vim.vm.ConfigSpec()
        spec_deviceChange_0 = vim.vm.device.VirtualDeviceSpec()
        spec_deviceChange_0.device = each
        spec_deviceChange_0.operation = "edit"
        spec.deviceChange = [spec_deviceChange_0]
        virtual_machine.ReconfigVM_Task(spec=spec)
