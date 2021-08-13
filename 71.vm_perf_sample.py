#!/usr/bin/env python
"""
 Written by Lance Hasson
 Github: https://github.com/JLHasson

 Script to report all available realtime performance metrics from a
 virtual machine. Based on a Java example available in the VIM API 6.0
 documentationavailable online at:
 https://pubs.vmware.com/vsphere-60/index.jsp?topic=%2Fcom.vmware.wssdk.pg.
 doc%2FPG_Performance.18.4.html&path=7_1_0_1_15_2_4

 Requirements:
     VM tools must be installed on all virtual machines.
"""
import os
import sys

import sys
sys.path.append(os.path.realpath(".") + '/venv/Lib/site-packages/')

from pyVim.connect import SmartConnect
from pyVmomi import vim
from tools import cli, service_instance


################################

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

    # parser = cli.Parser()
    # args = parser.get_args()
    # si = service_instance.connect(args)

    si = SmartConnect(host=serverDomain,
                      user=username,
                      pwd=password,
                      port=443, disableSslCertValidation=True)


    content = si.RetrieveContent()
    perf_manager = content.perfManager

    # create a mapping from performance stats to their counterIDs
    # counterInfo: [performance stat => counterId]
    # performance stat example: cpu.usagemhz.LATEST
    # counterId example: 6
    counter_info = {}
    for counter in perf_manager.perfCounter:
        full_name = counter.groupInfo.key + "." + \
                    counter.nameInfo.key + "." + counter.rollupType
        counter_info[full_name] = counter.key

    # create a list of vim.VirtualMachine objects so
    # that we can query them for statistics
    container = content.rootFolder
    view_type = [vim.VirtualMachine]
    recursive = True

    container_view = content.viewManager.CreateContainerView(container, view_type, recursive)
    children = container_view.view

    # Loop through all the VMs
    for child in children:
        # Get all available metric IDs for this VM
        counter_ids = [m.counterId for m in perf_manager.QueryAvailablePerfMetric(entity=child)]

        # Using the IDs form a list of MetricId
        # objects for building the Query Spec
        metric_ids = [vim.PerformanceManager.MetricId(
            counterId=counter, instance="*") for counter in counter_ids]

        # Build the specification to be used
        # for querying the performance manager
        spec = vim.PerformanceManager.QuerySpec(maxSample=1,
                                                entity=child,
                                                metricId=metric_ids)

        # Query the performance manager
        # based on the metrics created above
        result_stats = perf_manager.QueryStats(querySpec=[spec])

        # Loop through the results and print the output
        output = ""
        for _ in result_stats:
            output += " vm-name:        " + child.summary.config.name + "\n"
            for val in result_stats[0].value:
                # python3
                if sys.version_info[0] > 2:
                    counterinfo_k_to_v = list(counter_info.keys())[
                        list(counter_info.values()).index(val.id.counterId)]
                # python2
                else:
                    counterinfo_k_to_v = counter_info.keys()[
                        counter_info.values().index(val.id.counterId)]
                if val.id.instance == '':
                    output += child.summary.config.name + " - %s: %s\n" % (
                        counterinfo_k_to_v, str(val.value[0]))
                else:
                    output += child.summary.config.name + " %s (%s): %s\n" % (
                        counterinfo_k_to_v, val.id.instance, str(val.value[0]))

        print(output)


if __name__ == "__main__":
    main()
