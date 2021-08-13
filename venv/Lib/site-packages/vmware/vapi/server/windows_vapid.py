"""
vAPI windows provider
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


import os
import servicemanager
import sys
import traceback
import win32event
import win32serviceutil
import win32service

from vmware.vapi.server.vapid import create_servers, check_file_exists

#
# To create a new windows vAPI provider, create a new module for that
# provider like the one below.
#
# import os
# from windows_vapid import Vapid, handle_command_line
#
# class Sample(Vapid):
#     _svc_name_ = 'vAPISampleProvider'
#     _svc_display_name_ = 'vAPI Sample Provider'
#     _svc_description_ = 'Sample Provider'
#
#     def get_properties_file(self):
#         properties_dir = os.environ.get('SAMPLE_CONF')
#         return os.path.join(properties_dir, 'sample.properties')
#
# if __name__ == '__main__':
#     handle_command_line(Sample)
#
#
# Then set the SAMPLE_CONF environment variable with the
# absolute path of property file directory
#
# python.exe sample.py install
# python.exe sample.py start
#


class Vapid(win32serviceutil.ServiceFramework):
    """
    Wrapper class for vAPI providers on windows
    """

    # Used in the windows registry, should not contain spaces or
    # special characters preferably.
    _svc_name_ = 'vAPIProvider'
    # Used as the display name in the windows service manager
    _svc_display_name_ = 'vAPI Provider'
    # Used as the description for the service in windows service manager
    _svc_description_ = 'vAPI Provider'

    def __init__(self, *args):
        """
        Initialize Vapid on windows
        """
        win32serviceutil.ServiceFramework.__init__(self, *args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)

        # Get the properties file from environment variable
        # and configure the server
        properties_file = self.get_properties_file()
        try:
            check_file_exists(properties_file)
        except os.error as e:
            self.log(e)

        servers = create_servers(properties_file)
        if len(servers) == 0:
            self.log('No server available. Quit')
        self.server = servers[0]

    def get_properties_file(self):
        """
        Returns the properties file location for this provider

        :rtype: :class:`str`
        :return: Properties file absolute path
        """
        raise NotImplementedError

    @staticmethod
    def log(msg):
        """
        Utility for logging with the service manager
        """
        servicemanager.LogInfoMsg(str(msg))

    def svc_do_run(self):
        """
        Starts the vAPI provider
        """
        # pylint recognizes all the variables except ReportServiceStatus, since
        # pylint is tested only on linux environments now, disabling this error
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)  # pylint: disable=E1101
        try:
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)    # pylint: disable=E1101
            self.server.serve_forever()
            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
        except Exception:
            self.log(traceback.format_exc(sys.exc_info))
            self.SvcStop()
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)    # pylint: disable=E1101

    def svc_stop(self):
        """
        Stops the vAPI provider
        """
        # pylint recognizes all the variables except ReportServiceStatus, since
        # pylint is tested only on linux environments now, disabling this error
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)    # pylint: disable=E1101
        try:
            self.server.shutdown()
        except Exception:
            self.log(traceback.format_exc(sys.exc_info))
        win32event.SetEvent(self.stop_event)
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)    # pylint: disable=E1101


def handle_command_line(vapid):
    """
    Handle the command line arguments of windows service manager

    :type  vapid: :class:`vmware.vapi.server.vapid.Vapid`
    :param vapid: Class reference of Windows Vapid
    """
    win32serviceutil.HandleCommandLine(vapid)
