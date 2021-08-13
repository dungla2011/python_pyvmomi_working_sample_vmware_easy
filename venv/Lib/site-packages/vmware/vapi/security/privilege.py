"""
Privilege Validator interface
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2018 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from vmware.vapi.lib.log import get_vapi_logger

# Configure logging
logger = get_vapi_logger(__name__)


class PrivilegeValidator(object):
    """
    Interface for Privilege Validation
    """

    def validate(self, user_identity, required_privileges):
        """
        Validate the privileges required for a given user identity
        """
        raise NotImplementedError

    def __hash__(self):
        return str(self).__hash__()


# Privilege Validator instance
_privilege_validator = None


def get_privilege_validator(privilege_validator=None):
    """
    Returns the singleton PrivilegeValidator instance

    :type:  :class:`str`
    :param: Privilege Validator class
    """
    global _privilege_validator
    if _privilege_validator is None:
        _privilege_validator = privilege_validator()

    return _privilege_validator
