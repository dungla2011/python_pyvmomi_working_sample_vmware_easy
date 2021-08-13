"""
Written by Timo Sugliani
Github: https://github.com/tsugliani/

Code based on upload_file_to_vm snippet by Reubenur Rahman
Github: https://github.com/rreubenur/
"""
import os
import time
import re

import sys
sys.path.append(os.path.realpath(".") + '/venv/Lib/site-packages/')

from pyVim.connect import SmartConnect
from tools import cli, service_instance, pchelper
from pyVmomi import vim, vmodl




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


def main():
    """
    Simple command-line program for executing a process in the VM without the
    network requirement to actually access it.
    """
    si = SmartConnect(host=serverDomain,
                      user=username,
                      pwd=password,
                      port=443, disableSslCertValidation=True)

    try:
        content = si.RetrieveContent()

        for i in range(120, 121):
            vm_name = "win2012-test1_2021-08-12-" + str(i-100)

            print(vm_name)
            #
            # continue

            vm = pchelper.get_obj(content, [vim.VirtualMachine], vm_name)

            if not vm:
                raise SystemExit("Unable to locate the virtual machine.")

            tools_status = vm.guest.toolsStatus
            if tools_status in ('toolsNotInstalled', 'toolsNotRunning'):
                raise SystemExit(
                    "VMwareTools is either not running or not installed. "
                    "Rerun the script after verifying that VMwareTools "
                    "is running")

            creds = vim.vm.guest.NamePasswordAuthentication(
                username="administrator", password="123456abc"
            )

            try:
                profile_manager = content.guestOperationsManager.processManager

                path_to_program = "C:/windows/system32/netsh.exe"
                program_arguments = "interface ipv4 set address name=\"Ethernet0\" static 10.0.0." + str(i) + " 255.255.254.0 10.0.0.1"

                print(" program_arguments = " + program_arguments)

                program_spec = vim.vm.guest.ProcessManager.ProgramSpec(programPath=path_to_program,
                                                                       arguments=program_arguments)

                res = profile_manager.StartProgramInGuest(vm, creds, program_spec)

                if res > 0:
                    print("Program submitted, PID is %d" % res)
                    pid_exitcode = \
                        profile_manager.ListProcessesInGuest(vm, creds, [res]).pop().exitCode
                    # If its not a numeric result code, it says None on submit
                    while re.match('[^0-9]+', str(pid_exitcode)):
                        print("Program running, PID is %d" % res)
                        time.sleep(5)
                        pid_exitcode = \
                            profile_manager.ListProcessesInGuest(vm, creds, [res]).pop().exitCode
                        if pid_exitcode == 0:
                            print("Program %d completed with success" % res)
                            break
                        # Look for non-zero code to fail
                        elif re.match('[1-9]+', str(pid_exitcode)):
                            print("ERROR: Program %d completed with Failute" % res)
                            print("  tip: Try running this on guest %r to debug"
                                  % vm.summary.guest.ipAddress)
                            print("ERROR: More info on process")
                            print(profile_manager.ListProcessesInGuest(vm, creds, [res]))
                            break

                # input("...")
            except IOError as ex:
                print(ex)




    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
