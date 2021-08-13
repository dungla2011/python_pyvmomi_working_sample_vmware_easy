"""
Debugging utility
"""
__author__ = 'VMware, Inc'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import signal
import sys
import six
import traceback

from vmware.vapi.lib.log import get_vapi_logger

logger = get_vapi_logger(__name__)


def signal_usr1_handler(signal_number, stack_frame):  # pylint: disable=W0613
    """
    USR1 signal handler

    :type  signal_number: :class:`int`
    :param signal_number: signal number
    :type  stack_frame: frame object. See ``inspect``
    :param stack_frame: frame object
    """
    logger.error('---------------------- Begin dumping stack ----------------------')
    for tid, frame in six.iteritems(sys._current_frames()):  # pylint: disable=W0212
        logger.error('Thread id: %s\n%s',
                     str(tid),
                     ''.join(traceback.format_stack(frame)))
    logger.error('---------------------- End dumping stack ----------------------')

# Install signal handlers
signal_handlers_map = {}
if hasattr(signal, 'SIGUSR1'):
    signal_handlers_map[signal.SIGUSR1] = signal_usr1_handler

# Note: signal.signal() can only be called from main thread
for signal_num, handler in six.iteritems(signal_handlers_map):
    prev_handler = signal.signal(signal_num, handler)

# Only install signal handlers once
signal_handlers_map = {}
