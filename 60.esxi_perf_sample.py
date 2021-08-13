#!/usr/bin/env python
# William Lam
# www.virtuallyghetto.com

"""
vSphere Python SDK program for demonstrating vSphere perfManager API based on
Rbvmomi sample https://gist.github.com/toobulkeh/6124975
"""

import datetime
import os
import sys
sys.path.append(os.path.realpath(".") + '/venv/Lib/site-packages/')

from pyVim.connect import SmartConnect
from tools import cli, service_instance
from pyVmomi import vmodl, vim


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
        host = search_index.FindByDnsName(dnsName="10.0.1.11", vmSearch=False)

        perf_manager = content.perfManager
        metric_id = vim.PerformanceManager.MetricId(counterId=24, instance="*")
        start_time = datetime.datetime.now() - datetime.timedelta(hours=1)
        end_time = datetime.datetime.now()

        query = vim.PerformanceManager.QuerySpec(maxSample=1,
                                                 entity=host,
                                                 metricId=[metric_id],
                                                 startTime=start_time,
                                                 endTime=end_time)

        print(perf_manager.QueryPerf(querySpec=[query]))

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
