"""
Wsgi Application
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import os
import sys

from vmware.vapi.server.vapid import (create_servers, check_file_exists)


def setup_wsgi():
    """
    Setup WSGI server

    :rtype: `vmware.vapi.server.wsgi_server.WsgiServer`
    :return: WSGI server
    """
    spec = os.environ.get('VAPI_CONFIG')
    if spec is None:
        print('Please set the environment variable VAPI_CONFIG with properties '
              'file path')
        sys.exit(1)
    check_file_exists(os.path.abspath(spec))

    servers = create_servers(spec)
    return servers[0]

wsgi_server = setup_wsgi()
application = wsgi_server.get_wsgi_application()
