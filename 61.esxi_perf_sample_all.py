#!/usr/bin/env python
# William Lam
# www.virtuallyghetto.com

"""
vSphere Python SDK program for demonstrating vSphere perfManager API based on
Rbvmomi sample https://gist.github.com/toobulkeh/6124975
"""

import datetime
from pprint import pprint

import os


import sys
sys.path.append(os.path.realpath(".") + '/venv/Lib/site-packages/')

################################

from pyVim.connect import SmartConnect
from tools import cli, service_instance
from pyVmomi import vmodl, vim
import sys


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
   Simple command-line program demonstrating vSphere perfManager API
   """

    # parser = cli.Parser()
    # parser.add_required_arguments(cli.Argument.VIHOST)
    # args = parser.get_args()
    # si = service_instance.connect(args)

    si = SmartConnect(host=serverDomain,
                      user=username,
                      pwd=password,
                      port=443, disableSslCertValidation=True)

    try:
        content = si.RetrieveContent()

        search_index = content.searchIndex
        # quick/dirty way to find an ESXi host
        # host = search_index.FindByDnsName(dnsName=args.vihost, vmSearch=False)

        # Get one host
        host = search_index.FindByDnsName(dnsName="10.0.1.11", vmSearch=False)

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

        # Print Pair of: counterId and name
        # samples:
        # 'cpu.totalmhz.average': 264,
        # 'cpu.usage.average': 2,
        # 'cpu.usage.maximum': 4,
        # 'cpu.usage.minimum': 3,
        # pprint(counter_info)
        # quit()

        counter_ids = [m.counterId for m in perf_manager.QueryAvailablePerfMetric(entity=host)]

        metric_ids = [vim.PerformanceManager.MetricId(
            counterId=counter, instance="*") for counter in counter_ids]
        start_time = datetime.datetime.now() - datetime.timedelta(hours=1)
        # start_time = datetime.datetime.now() - datetime.timedelta(minutes=30)
        # start_time = datetime.datetime.now() - datetime.timedelta(seconds=7600)
        end_time = datetime.datetime.now()

        # Build the specification to be used
        # for querying the performance manager
        spec = vim.PerformanceManager.QuerySpec(maxSample=5,
                                                entity=host,
                                                # intervalId=300,
                                                intervalId=20,
                                                metricId=metric_ids,
                                                startTime=start_time,
                                                endTime=end_time)

        # Query the performance manager
        # based on the metrics created above
        result_stats = perf_manager.QueryStats(querySpec=[spec])

        print(result_stats)

        output = ""
        for _ in result_stats:
            print(" host-name:        " + host.summary.config.name)
            for val in result_stats[0].value:
                # python3
                if sys.version_info[0] > 2:
                    # print("CountId = " + str(val.id.counterId))
                    counterinfo_k_to_v = list(counter_info.keys())[
                        list(counter_info.values()).index(val.id.counterId)]
                # python2
                else:
                    counterinfo_k_to_v = counter_info.keys()[
                        counter_info.values().index(val.id.counterId)]

                print("--- CountId = " + str(val.id.counterId))

                print(" Total = " + str(len(val.value)))
                # Tổng hợp Using Resource của từng device, không có chi tiết như từng core cpu, từng card mạng
                if val.id.instance == '':
                    for i in range(0, len(val.value)):
                        vx = val.value[i]
                        timex = str(result_stats[0].sampleInfo[i].timestamp)
                        print(str(i) + " . " + timex + " - (Sumary) %s  = %s" % (counterinfo_k_to_v, str(vx)))
                        # print("Name/value: %s  = %s" % (counterinfo_k_to_v, str(val.value[0])))
                        # print("Name/value1: %s  = %s" % (counterinfo_k_to_v, str(val.value[1])))
                        if os.path.exists("/share/vcenter_status/"):
                            file_object = open("/share/vcenter_status/" + counterinfo_k_to_v, 'a')
                            file_object.write(timex + "#" + str(vx) + "\n")
                            file_object.close()

                # Chi tiết, ví dụ từng core, card mạng
                else:
                    for i in range(0, len(val.value)):
                        vx = val.value[i]
                        timex = str(result_stats[0].sampleInfo[i].timestamp)
                        print(str(i) + " . " + timex + " - (Detail) %s (%s): %s" % (
                        counterinfo_k_to_v, val.id.instance, str(vx)))
                        # print("%s (%s): %s" % (counterinfo_k_to_v, val.id.instance, str(val.value[0])))

        # print(output)

        # metric_id = vim.PerformanceManager.MetricId(counterId=24, instance="*")
        # start_time = datetime.datetime.now() - datetime.timedelta(hours=1)
        # end_time = datetime.datetime.now()
        #
        # query = vim.PerformanceManager.QuerySpec(maxSample=1,
        #                                          entity=host,
        #                                          metricId=[metric_id],
        #                                          startTime=start_time,
        #                                          endTime=end_time)

        # print(perf_manager.QueryPerf(querySpec=[query]))

    except vmodl.MethodFault as ex:
        print("Caught vmodl fault : " + ex.msg)
        return -1
    except Exception as ex:
        print("Caught exception : " + str(ex))
        return -1

    return 0


# Start program
if __name__ == "__main__":
    main()
