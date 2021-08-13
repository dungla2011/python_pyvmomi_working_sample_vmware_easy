import os
import sys

import requests
import urllib3

import sys
sys.path.append(os.path.realpath(".") + '/venv/Lib/site-packages/')

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

# print(ret)
for ob in ret:
    print(ob)
