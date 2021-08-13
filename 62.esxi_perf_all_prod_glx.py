#!/usr/bin/env python
# William Lam
# www.virtuallyghetto.com

"""
vSphere Python SDK program for demonstrating vSphere perfManager API based on
Rbvmomi sample https://gist.github.com/toobulkeh/6124975
"""

import datetime
import time
from pprint import pprint

import sys, os

sys.path.append(os.path.realpath(".") + '/venv/Lib/site-packages/')

# from datetime import datetime

from pyVim.connect import SmartConnect
from tools import cli, service_instance
from pyVmomi import vmodl, vim
import sys
import subprocess


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

    get5m = 0
    if len(sys.argv) > 1 and sys.argv[1] == "get5m":
        print(" get 5m")
        get5m = 1

    now = datetime.datetime.now()
    fileStr = "#" + now.strftime("%Y-%m-%d_%H")
    folderPath = "/share/vcenter_status/"
    if get5m:
        folderPath = "/share/vcenter_5m_status/"

    if not os.name == "nt":
        if not os.path.exists(folderPath):
            os.mkdir(folderPath)


    cc = 0
    while (True):

        cc += 1

        if cc % 2 == 0:
            get5m = 1

        print(" Looping..." + str(datetime.datetime.now()))

        si = SmartConnect(host=serverDomain,
                          user=username,
                          pwd=password,
                          port=443, disableSslCertValidation=True)

        try:
            content = si.RetrieveContent()

            mm_host = ['10.0.1.11', '10.0.1.12', '10.0.1.13', '10.0.1.14', '10.0.1.99', ]

            # hostName = "10.0.1.13"

            for hostName in mm_host:

                search_index = content.searchIndex
                # quick/dirty way to find an ESXi host
                # host = search_index.FindByDnsName(dnsName=args.vihost, vmSearch=False)
                host = search_index.FindByDnsName(dnsName=hostName, vmSearch=False)

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

                counter_ids = [m.counterId for m in perf_manager.QueryAvailablePerfMetric(entity=host)]

                metric_ids = [vim.PerformanceManager.MetricId(
                    counterId=counter, instance="*") for counter in counter_ids]

                hour1 = 1
                interval = 20

                if get5m:
                    interval = 300
                    # hour1 = 12

                start_time = datetime.datetime.now() - datetime.timedelta(hours=hour1)
                # start_time = datetime.datetime.now() - datetime.timedelta(minutes=30)
                # start_time = datetime.datetime.now() - datetime.timedelta(seconds=7600)
                end_time = datetime.datetime.now()



                # Build the specification to be used
                # for querying the performance manager
                spec = vim.PerformanceManager.QuerySpec(maxSample=180,
                                                        entity=host,
                                                        intervalId=interval,
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
                                print(str(i) + " . " + timex + " - (Summary) %s  = %s" % (counterinfo_k_to_v, str(vx)))
                                if os.path.exists(folderPath):
                                    fpath = folderPath + hostName + "#" + counterinfo_k_to_v + "" + fileStr
                                    print(" fpath = " + fpath)
                                    # input("...")
                                    file_object = open(fpath, 'a')
                                    file_object.write(timex + "#" + str(vx) + "\n")
                                    file_object.close()

                        # Chi tiết, ví dụ từng core, card mạng
                        else:
                            for i in range(0, len(val.value)):
                                vx = val.value[i]
                                timex = str(result_stats[0].sampleInfo[i].timestamp)
                                print(str(i) + " . " + timex + " - (Detail) %s (%s): %s" % (
                                    counterinfo_k_to_v, val.id.instance, str(vx)))



            os.system("php /var/www/galaxycloud/tool/_site/galaxycloud/cron/update_server_resource_usage.php")

        except vmodl.MethodFault as ex:
            print("Caught vmodl fault : " + ex.msg)
            return -1
        except Exception as ex:
            print("Caught exception : " + str(ex))
            return -1

        print(" Sleep 300 ..." + str(datetime.datetime.now()))
        time.sleep(300)

    return 0


# Start program
if __name__ == "__main__":
    main()
