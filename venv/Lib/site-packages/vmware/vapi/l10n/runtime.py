"""
Helper class for internationalization of the runtime messages
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


from vmware.vapi.l10n.bundle import PropertiesResourceBundle
from vmware.vapi.l10n.formatter import StringFormatter
from vmware.vapi.message import MessageFactory


def get_runtime_message_factory():
    """
    Default message factory. Load the runtime message bundle from
    the egg file

    :rtype: :class:`vmware.vapi.message.MessageFactory`
    :return: Message factory class for the runtime
    """
    msg_bundle = PropertiesResourceBundle(
        [('vmware.vapi.settings', 'runtime.properties')])
    return MessageFactory(msg_bundle, StringFormatter)


# MessageFactory instance for the runtime
message_factory = get_runtime_message_factory()
