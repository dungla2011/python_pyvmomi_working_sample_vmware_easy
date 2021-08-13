"""
Helper module to build value passed in UserAgent header
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2018 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import platform

from pkg_resources import (working_set, Requirement, Distribution)

class UserAgentBuilder:
    """ Builder for the value to be passed in UserAgent header """
    VSHPERE_SDK_DIST_NAME = 'vapi-client-bindings'
    def __init__(self):
        self.product_version = None
        self.vapi_version = None
        self.user_agent = self.build()
        self.load_sdk_version()

    def build(self):
        if not self.vapi_version:
            vapi_runtime_dist = working_set.find(Requirement.parse('vapi-runtime'))
            self.vapi_version = vapi_runtime_dist.version if vapi_runtime_dist else ''
        python_version = platform.python_version()
        # platform.uname() returns (system, node, release, version, machine, processor)
        (os_name,_,os_version,_,os_arch,_) = platform.uname()

        self.user_agent = "vAPI/%s Python/%s (%s; %s; %s)"%(self.vapi_version,
            python_version, os_name, os_version, os_arch)
        if self.product_version:
            self.user_agent = "%s %s" % (self.product_version, self.user_agent)

        return self.user_agent.strip()

    def load_sdk_version(self):
        if self.product_version:
            # Product version already set, do nothing
            return
        # TODO: Even if multiple SDKs are loaded, version is collected only
        # from the vsphere client bindings wheel/distribution. Might need to
        # support multiple SDKs in the future
        sdk_dist = working_set.find(Requirement.parse(self.VSHPERE_SDK_DIST_NAME))
        if sdk_dist:
            self.set_product_info('SDK', sdk_dist.version)

    def set_product_info(self,name, version, product_comment=None, vapi_version=None):
        self.product_version = "%s/%s"%(name, version)
        if product_comment:
            self.product_version += " (%s)" % product_comment
        if vapi_version is not None:
            self.vapi_version = vapi_version
        self.build()

_user_agent_builder = UserAgentBuilder()

def init_product_info(name, version, product_comment=None, vapi_version=None):
    """
    Initializes details of the application layer that need to be passed
    as part of the user agent header

    Example:
    calling init_product_info('DCLI', 2.10.0, product_comment='i', vapi_version=2.9.1)
    would produced User-Agent header:
    DCLI/2.10.0 (i) vAPI/2.9.1 Python/2.7.13+ (Linux; 4.13.0-45-generic; x86_64)

    :type  name: :class:`str`
    :param name: Service identifier
    :type  version: :class:`str`
    :param version: Operation identifier
    :type  product_comment: :class:`str`
    :param product_comment: Adds additional comment to the name and version data
    :type  vapi_version: :class:`str`
    :param vapi_version: Specifies vapi version to use explicitly
    """
    global _user_agent_builder
    _user_agent_builder.set_product_info(name,
                                         version,
                                         product_comment=product_comment,
                                         vapi_version=vapi_version)

def get_user_agent():
    """
    Gets the string that needs to be passed in the UserAgent header

    :rtype: :class:`str`
    :return: UserAgent value
    """
    global _user_agent_builder
    return _user_agent_builder.user_agent
