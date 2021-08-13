"""
Message factory and Error factory
"""
__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from six import with_metaclass

from com.vmware.vapi.std_provider import LocalizableMessage
from com.vmware.vapi.std import errors_provider
from vmware.vapi.l10n.formatter import StringFormatter
from vmware.vapi.l10n.bindings import MessageArgumentConverter
from vmware.vapi.l10n.bundle import (
    DictionaryResourceBundle, PropertiesResourceBundle)
from vmware.vapi.bindings.error import VapiError
from vmware.vapi.lib.converter import Converter


#
# This is a message factory that creates instances of LocalizableMessage
# classes. This is for static bindings clients and providers.
#
class LocalizableMessageFactory(object):
    """
    Utility class for creating Localizable messages
    """
    def __init__(self, resource_bundle, formatter):
        """
        Initialize LocalizableMessageFactory

        :type  resource_bundle:
            :class:`vmware.vapi.l10n.bindings.ResourceBundle`
        :param resource_bundle: Resource bundle object
        :type  formatter: :class:`vmware.vapi.message.MessageFormatter`
        :param formatter: Message formatter object
        """
        self._resource_bundle = resource_bundle
        self._formatter = formatter

    @staticmethod
    def _build_unavailable_message(id_, args):
        """
        Create a localizable message for the case when message id is not present
        in the resource bundle

        :type  id_: :class:`str`
        :param id_: Message identifier
        :type  args: :class:`list` of :class:`str`
        :param args: Arguments for the message
        """
        def_msg = 'Unknown message ID %s requested with parameters %s'
        string_args = ', '.join(args)
        return LocalizableMessage(
            id='vapi.message.unknown',
            default_message=def_msg % (id_, string_args),
            args=[id_, string_args])

    @staticmethod
    def _build_invalid_message(id_, args):
        """
        Create a localizable message for the case when message arguments
        could not be converted

        :type  id_: :class:`str`
        :param id_: Message identifier
        :type  args: :class:`list` of :class:`object`
        :param args: Arguments for the message
        """
        def_msg = 'Invalid arguments %s for message ID %s'
        string_args = repr(args)
        return LocalizableMessage(
            id='vapi.message.invalid',
            default_message=def_msg % (id_, string_args),
            args=[id_, string_args])

    def get_message(self, id_, *args):
        """
        Return a message object for the given id with the given args.
        If the message is not found, a default unknown message is returned.

        :type  id_: :class:`str`
        :param id_: The unique message identifier
        :type  args: :class:`list` of :class:`object`
        :param args: The arguments to be used for constructing this message

        :rtype: :class:`com.vmware.vapi.std_provider.LocalizableMessage`
        :return: The message object constructed using the given arguments
        """
        try:
            string_args = MessageArgumentConverter.to_string(args)
        except TypeError:
            return self._build_invalid_message(id_, args)

        try:
            template = self._resource_bundle.get(id_)
            default_msg = self._formatter.format_msg(template,
                                                     args)
            return LocalizableMessage(id=id_,
                                      default_message=default_msg,
                                      args=string_args)
        except KeyError:
            return self._build_unavailable_message(id_, string_args)


#
# XXX: Deprecated. All classes should use LocalizableMessageFactory now.
# Once all implementations are migrated to LocalizableMessageFactory, this will
# be deleted.
#
class MessageFactory(LocalizableMessageFactory):
    """
    A factory class to generate localizable messages using messages from
    the dictionary that is passed by the user.
    """
    def __init__(self, message_dict):
        """
        Initializes MessageFactory

        :type  message_dict: :class:`dict`
        :param message_dict: The message dictionary for the message factory
        """
        LocalizableMessageFactory.__init__(
            self,
            DictionaryResourceBundle(message_dict),
            StringFormatter)


class PropertiesMessageFactory(LocalizableMessageFactory):
    """
    A factory class to generate localizable messages using messages from
    properties files in the egg files.
    """
    def __init__(self, property_files):
        """
        Initializes PropertiesMessageFactory

        :type  property_files: :class:`list` of :class:`str`
        :param property_files: List of property files to be processed
        """
        LocalizableMessageFactory.__init__(
            self,
            PropertiesResourceBundle(property_files),
            StringFormatter)


def enumerate_standard_error_names():
    """
    Enumerate the class names of all the standard errors

    :rtype: :class:`list` of :class:`str`
    :return: Class names of all the standard errors
    """
    return [name for name in dir(errors_provider)
            if getattr(errors_provider, name) is not VapiError
            and isinstance(getattr(errors_provider, name), type)
            and issubclass(getattr(errors_provider, name), VapiError)]


class _ErrorFactoryMetaclass(type):
    """
    Metaclass for the ErrorFactory class that dynamically implements
    factory methods for all the standard error types.
    """
    METHOD_PREFIX = 'new_'
    METHOD_PREFIX_LENGTH = len(METHOD_PREFIX)

    def __getattr__(cls, name):
        """
        Return a synthesized factory method if the given name matches the
        name of one of the standard error types (after converting from
        lower-case-with-underscores to cap-words).
        """
        if name.startswith(cls.METHOD_PREFIX) and name is not 'new_vapi_error':
            canonical_error_type_name = name[cls.METHOD_PREFIX_LENGTH:]
            capwords_error_type_name = Converter.underscore_to_capwords(
                canonical_error_type_name)
            error_type = getattr(errors_provider, capwords_error_type_name)
            if (isinstance(error_type, type) and
                    issubclass(error_type, VapiError)):
                def factory_method(**kwargs):
                    """
                    Synthesized factory function for a standard error type.
                    """
                    return error_type(**kwargs)
                return factory_method
        msg = "type object '%s' has no attribute '%s'" % (cls.__name__, name)
        raise AttributeError(msg)

    def __dir__(cls):
        """
        Return the names of the factory methods that are synthesized for each of
        standard error types in addition to the name of the attributes in the
        base class (object).
        """
        #pylint: disable=R0201
        method_names = ['new_' + Converter.capwords_to_underscore(name)
                        for name in enumerate_standard_error_names()]
        return sorted(dir(object) + method_names)


class ErrorFactory(with_metaclass(_ErrorFactoryMetaclass, object)):
    """
    Factory class for creating standard errors
    """

    def __init__(self):
        """
        Initialize ErrorFactory
        """
        pass

    @classmethod
    def get_standard_error_types(cls):
        """
        Return the binding types of all the standard errors

        :rtype: :class:`list` of :class:`vmware.vapi.bindings.type.ErrorType`
        :return: Binding types of all the standard errors
        """
        return [getattr(errors_provider, name).get_binding_type()
                for name in enumerate_standard_error_names()]
