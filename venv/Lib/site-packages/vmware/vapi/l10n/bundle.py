"""
Helper classes for creation of resource bundles
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import six

from vmware.vapi.message import MessageBundle


def _parse_message_data_sets(data_sets):
    """
    Parse the message data sets and extract the messages

    :type  data_sets: :class:`list` of :class:`str`
    :param data_sets: Resource bundle string extracted from the egg file
    :rtype: :class:`dict` of :class:`str`, :class:`str`
    :return: Dictionary of messages
    """
    result = {}
    for data_set in data_sets:
        messages = data_set.splitlines()
        for message in messages:
            if isinstance(message, six.binary_type):
                message = message.decode('utf-8')
            message = message.strip()
            if not message.startswith('#') and '=' in message:
                key, value = message.split('=', 1)
                key = key.strip()
                # To use '=' in the value, it has to be escaped
                value = value.strip().replace(r'\=', '=')
                if not key:
                    raise ValueError('Key not present for value %s', value)
                if not value:
                    raise ValueError('Value not present for key %s', value)
                result[key] = value
    return result


class PropertiesResourceBundle(MessageBundle):
    """
    Class for creating resource bundles using property files in the
    distributable. i.e. egg or zip file.
    """
    def __init__(self, property_files):
        """
        Initialize PropertiesResourceBundle

        :type  property_files: :class:`list` of :class:`tuple` or :class:`tuple`
        :param property_files: List of property files to be processed. The tuple
            should be of the form (package, resource_name). For ex: If a file
            named runtime.properties is present in vmware.vapi package, the
            tuple to be passed is ('vmware.vapi', 'runtime.properties')
        """
        # Importing here so that there is no dependency on pkg_resources
        # for modules that use other kind of MessageBundle classes
        from pkg_resources import resource_string
        if not isinstance(property_files, list):
            property_files = [property_files]
        bundles = [resource_string(path, filename)
                   for path, filename in property_files]
        messages = _parse_message_data_sets(bundles)
        MessageBundle.__init__(self, messages)


class FileMessageBundle(MessageBundle):
    """
    Class for creating resource bundles using list of files
    that contain messages
    """
    def __init__(self, message_files):
        """
        Initialize FileMessageBundle

        :type  message_files: :class:`list` of :class:`str` or :class:`str`
        :param message_files: List of message files to be processed. Each
            element in the list should be a fully qualified file path.
        """
        if not isinstance(message_files, list):
            message_files = [message_files]
        bundles = []
        for message_file in message_files:
            if six.PY2:
                with open(message_file, 'r') as fp:
                    bundles.append(fp.read())
            else:
                with open(message_file, 'r', encoding='utf-8') as fp:
                    bundles.append(fp.read())
        messages = _parse_message_data_sets(bundles)
        MessageBundle.__init__(self, messages)


class DictionaryResourceBundle(MessageBundle):
    """
    Class for creating resource bundles using dictionary of messages
    """
    def __init__(self, msgs):
        """
        Initialize DictionaryResourceBundle

        :type  msgs: :class:`dict`
        :param msgs: Message bundle
        """
        if not isinstance(msgs, dict):
            raise TypeError('Messages should be a dictionary')
        MessageBundle.__init__(self, msgs)
