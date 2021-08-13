

#----------------- Start of code capture -----------------
import os

import sys
sys.path.append(os.path.realpath(".") + '/venv/Lib/site-packages/')


from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
from tools import cli, pchelper, service_instance
from pprint import pprint
from tools import cli, service_instance, tasks, pchelper


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


vm_name = "2012-linhtest112"


si = SmartConnect(host=serverDomain,
                                user=username,
                                pwd=password,
                                port=443,disableSslCertValidation=True)


#---------------ReconfigVM_Task---------------
spec = vim.vm.ConfigSpec()
spec_deviceChange_0 = vim.vm.device.VirtualDeviceSpec()
spec_deviceChange_0.device = vim.vm.device.VirtualDisk()
# spec_deviceChange_0.device.shares = vim.SharesInfo()
# spec_deviceChange_0.device.shares.shares = 1000
# spec_deviceChange_0.device.shares.level = 'normal'
#spec_deviceChange_0.device.capacityInBytes = 21489516544
spec_deviceChange_0.device.storageIOAllocation = vim.StorageResourceManager.IOAllocationInfo()
# spec_deviceChange_0.device.storageIOAllocation.shares = vim.SharesInfo()
# spec_deviceChange_0.device.storageIOAllocation.shares.shares = 1000
# spec_deviceChange_0.device.storageIOAllocation.shares.level = 'normal'
spec_deviceChange_0.device.storageIOAllocation.limit = 222
# spec_deviceChange_0.device.storageIOAllocation.reservation = 0
spec_deviceChange_0.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
# spec_deviceChange_0.device.backing.backingObjectId = ''
# spec_deviceChange_0.device.backing.fileName = '[s1-1tb_nvme_ssd_166] 2012-linhtest1/2012-linhtest1.vmdk'
# spec_deviceChange_0.device.backing.split = False
# spec_deviceChange_0.device.backing.writeThrough = False
# spec_deviceChange_0.device.backing.datastore = si.FindByUuid(None, "datastore-12009", True, True)   #SearchIndex
# spec_deviceChange_0.device.backing.contentId = '67a9696108b16953d90feaf783227a48'
# spec_deviceChange_0.device.backing.thinProvisioned = True
spec_deviceChange_0.device.backing.diskMode = 'persistent'
# spec_deviceChange_0.device.backing.digestEnabled = False
# spec_deviceChange_0.device.backing.sharing = 'sharingNone'
# spec_deviceChange_0.device.backing.uuid = '6000C290-f25f-00bc-3fdd-66c7c14e069c'
spec_deviceChange_0.device.controllerKey = 1000
spec_deviceChange_0.device.unitNumber = 0
# spec_deviceChange_0.device.nativeUnmanagedLinkedClone = False
# spec_deviceChange_0.device.capacityInKB = 20985856
# spec_deviceChange_0.device.deviceInfo = vim.Description()
# spec_deviceChange_0.device.deviceInfo.summary = '20,985,856 KB'
# spec_deviceChange_0.device.deviceInfo.label = 'Hard disk 1'
# spec_deviceChange_0.device.diskObjectId = '678-2000'
spec_deviceChange_0.device.key = 2000
spec_deviceChange_0.operation = "edit"
spec.deviceChange = [spec_deviceChange_0]
spec.cpuFeatureMask = []



content = si.RetrieveContent()

# print(content)

vm = pchelper.get_obj(content, [vim.VirtualMachine], vm_name)

print("VM1")
print(vm)
print("VMName: " + vm.name)


task = vm.ReconfigVM_Task(spec=spec)
tasks.wait_for_tasks(si, [task])

