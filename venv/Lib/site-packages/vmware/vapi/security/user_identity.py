"""
User Identity class
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


class UserIdentity(object):
    """
    User Identity class represents result for Authentication
    Handler authenticate method.
    """

    def __init__(self, username, domain=None):
        """
        Initialize User Identity
        """
        self._username = username
        self._domain = domain

    def get_username(self):
        """
        Return user name

        :rtype: :class:`str`
        :return: Username
        """
        return self._username

    def get_domain(self):
        """
        Return domain name

        :rtype: :class:`str`
        :return: Domain name
        """
        return self._domain
