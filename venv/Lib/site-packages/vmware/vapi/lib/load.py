"""
Convenience methods for dynamic loading
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import six

from vmware.vapi.lib.log import get_vapi_logger

logger = get_vapi_logger(__name__)


def dynamic_import(constructor):
    """
    Dynamically import a module and get the specified module attribute

    :type    constructor: :class:`str`
    :param   constructor: Fully qualified module attribute
    :rtype:  :class:`object`
    :return: Python object
    """
    target_attr = None
    if constructor:
        if isinstance(constructor, six.string_types):
            try:
                # Handle case where there's no dot in the module name
                if constructor.find('.') != -1:
                    module_name, fn = constructor.rsplit('.', 1)
                    module = __import__(module_name, globals(), locals(), [fn])
                    target_attr = getattr(module, fn)
                else:
                    target_attr = __import__(constructor, globals(), locals())
            except ImportError as err:
                logger.exception('Import failed: %s: module %s fn %s',
                                 str(err), module_name, fn)
                target_attr = None
            except AttributeError as err:
                logger.exception('Import failed: Module %s has no %s',
                                 module_name, fn)
                target_attr = None
    return target_attr


def dynamic_import_list(constructors):
    """
    Dynamically import a list of modules

    :type    constructors: :class:`list` of :class:`str`
    :param   constructors: List of fully qualified module attributes
    :rtype:  :class:`list` of :class:`object`
    :return: List of imported python objects
    """
    return [dynamic_import(c) for c in constructors]
