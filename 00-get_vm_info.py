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

vm_name = "GlxU18-D900-121.188"
vm_name = "w10-local-admin-216.250"


si = SmartConnect(host=serverDomain,
                                user=username,
                                pwd=password,
                                port=443, disableSslCertValidation=True)

content = si.RetrieveContent()

# print(content)

vm = pchelper.get_obj(content, [vim.VirtualMachine], vm_name)
# if vmuuid:
#     search_index = si.content.searchIndex
#     vm = search_index.FindByUuid(None, vmuuid, True)
# elif vm_name:
#     content = si.RetrieveContent()
#     vm = pchelper.get_obj(content, [vim.VirtualMachine], vm_name)

def print_vm_info(virtual_machine):
    """
    Print information for a particular virtual machine or recurse into a
    folder with depth protection
    """
    # vm = child.summary.config.name
    # # check for the VM
    # if (vm == vmName):
    #     vmSummary = child.summary
    #     # get the diskInfo of the selected VM
    #     info = vmSummary.vm.guest.disk

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

    print("Template   : ", summary.config.template)
    print("Path       : ", summary.config.vmPathName)
    print("Guest      : ", summary.config.guestFullName)
    print("Instance UUID : ", summary.config.instanceUuid)
    print("Bios UUID     : ", summary.config.uuid)
    annotation = summary.config.annotation
    if annotation:
        print("Annotation : ", annotation)
    print("State      : ", summary.runtime.powerState)
    if summary.guest is not None:
        ip_address = summary.guest.ipAddress
        tools_version = summary.guest.toolsStatus
        if tools_version is not None:
            print("VMware-tools: ", tools_version)
        else:
            print("Vmware-tools: None")
        if ip_address:
            print("IP         : ", ip_address)
        else:
            print("IP         : None")
    if summary.runtime.question is not None:
        print("Question  : ", summary.runtime.question.text)
    print("")

print_vm_info(vm)

print("VM1")
print(vm)
print("VMName: " + vm.name)
pprint(vars(vm))

var = vars(vm)
print(" OBJ TYPE = ", type(var))
print(" MOID = ", var['_moId'])

