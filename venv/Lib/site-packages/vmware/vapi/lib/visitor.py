"""
Visitor helper class
"""
__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from vmware.vapi.lib.converter import Converter


class VapiVisitor(object):
    """
    Convenience class for visitors used in vAPI Python runtime
    """
    def __init__(self, suffix=None):
        """
        Initialize VapiVisitor

        :type  suffix: :class:`str`
        :param suffix: The suffix string that should be removed from
                       class name during the dispatch
        """
        self._suffix = suffix
        self._cache = {}
        object.__init__(self)

    def visit(self, value):
        """
        Dispatch the call to the appropriate method based
        on the type of the input argument

        :type  value: :class:`object`
        :param value: The object to be used for dispatch
        """
        class_name = value.__class__.__name__
        method = self._cache.get(class_name)
        if not method:
            type_name = class_name
            if self._suffix and type_name.endswith(self._suffix):
                type_name = type_name[:-len(self._suffix)]
            type_name = Converter.capwords_to_underscore(type_name)
            method = getattr(self, 'visit_' + type_name)
            self._cache[class_name] = method
        return method(value)
