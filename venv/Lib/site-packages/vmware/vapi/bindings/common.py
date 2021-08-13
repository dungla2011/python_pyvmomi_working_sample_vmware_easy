"""
Bindings common module that contains common code for skeletons and stubs
"""
__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


from vmware.vapi.exception import CoreException


def raise_core_exception(msg_list):
    """
    Create and raise a CoreException from a list of messages

    :type msg_list: :class:`vmware.vapi.message.Message`
    :param msg_list: List of messages

    :raise: CoreException if msg list is not empty
    """
    exception = None
    if msg_list:
        for msg in reversed(msg_list):
            if exception:
                exception = CoreException(msg, cause=exception)
            else:
                exception = CoreException(msg)
    if exception is not None:
        raise exception  # pylint: disable-msg=E0702


class NameToTypeResolver(object):
    """
    Helper class that resolves a fully qualified canonical type name to a type
    descriptor. The type name can be a structure name or an error name.
    """
    def __init__(self, type_map):
        """
        Initialize NameToTypeResolver

        :type  type_map: :class:`dict` of :class:`str` and :class:`VapiStruct`
        :param type_map: Type map that contains the canonical names and the
            references to the binding classes for these types.
        """
        self._type_map = type_map

    def resolve(self, name):
        """
        Type name to be resolved
        """
        return self._type_map.get(name)
