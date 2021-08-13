#!/usr/bin/env python

"""
List of Data types supported
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


class Type(object):
    """
    Enum of all the data types used in vAPI Runtime
    """
    INTEGER = 'Integer'
    DOUBLE = 'Double'
    BOOLEAN = 'Boolean'
    STRING = 'String'
    BLOB = 'Blob'
    LIST = 'List'
    STRUCTURE = 'Structure'
    OPTIONAL = 'Optional'
    VOID = 'Void'
    OPAQUE = 'Opaque'
    SECRET = 'Secret'
    ERROR = 'Error'
    STRUCTURE_REF = 'StructureRef'
    DYNAMIC_STRUCTURE = 'DynamicStructure'
    ANY_ERROR = 'AnyError'
