"""
vAPI Message class
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


#
# This is a message class that can be used by runtime classes.
#
class Message(object):
    """
    This class encapsulates the concept of a localizable message.

    :type id_: :class:`string`
    :ivar id_: The unique message identifier
    :type def_msg: :class:`string`
    :ivar def_msg: An english language default
    :type args: :class:`list` of :class:`string`
    :ivar args: The arguments to be used for the messsage
    """
    def __init__(self, id_, def_msg, *args):
        """
        Initializes the message object

        :type  id_: :class:`string`
        :param id_: The unique message identifier
        :type  def_msg: :class:`string`
        :param def_msg: An english language default
        :type  args: :class:`list` of :class:`string`
        :param args: The arguments to be used for the messsage
        """
        self.id = id_
        self.def_msg = def_msg
        self.args = args

    def __eq__(self, other):
        return (isinstance(other, Message) and
                (self.id == other.id) and
                (self.def_msg == other.def_msg) and
                (self.args == other.args))

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return 'Message(id_=%s, def_msg=%s, args=%s)' % (repr(self.id),
                                                         repr(self.def_msg),
                                                         repr(self.args))

    def __str__(self):
        return self.def_msg


class MessageFormatter(object):
    """
    Base class for all message formatter classes
    """
    @classmethod
    def format_msg(cls, msg, args):
        """
        Format the message using the specified arguments

        :type  msg: :class:`str`
        :param msg: Message template
        :type  args: :class:`list` of :class:`object`
        :param args: Arguments for the message
        :rtype: :class:`str`
        :return: Localized message
        """
        raise NotImplementedError


class MessageBundle(object):
    """
    Base class for all message bundle classes.
    """
    def __init__(self, messages):
        """
        Initialize MessageBundle.

        :type  messages: :class:`dict` of :class:`str`, :class:`str`
        :param messages: Dictionary with message identifiers as keys and
            message templates as values.
        """
        self._messages = messages

    def get(self, msg_id):
        """
        Returns the message template for the given message identifier

        :type  msg_id: :class:`str`
        :param msg_id: Message identifier
        :rtype: :class:`str`
        :return: Message template
        :raise KeyError: If the message identifier is not found
        """
        return self._messages[msg_id]


class MessageFactory(object):
    """
    A factory class to generate localizable messages
    """
    def __init__(self, msg_bundle, formatter):
        """
        Initializes the message object

        :type  msg_bundle: :class:`MessageBundle`
        :param messages: The message dictionary for the message factory
        :type  formatter: :class:`vmware.vapi.formatter.MessageFormatter`
        :param formatter: Formatter for the message
        """
        self._msg_bundle = msg_bundle
        self._formatter = formatter

    def get_message(self, id_, *args):
        """
        Return a message object for the given id with the given args.
        If the message is not found, a default unknown message is returned.

        :type  id_: string
        :param id_: The unique message identifier
        :type  args: :class:`list` of :class:`object`
        :param args: The arguments to be used for constructing this message
        :rtype: :class:`Message`
        :return: The message object constructed using the given arguments
        """
        try:
            msg = self._msg_bundle.get(id_)
            def_msg = self._formatter.format_msg(msg,
                                                 args)
            return Message(id_, def_msg, *args)
        except KeyError:
            return Message(
                'vapi.message.unknown',
                'Unknown message ID %s requested with parameters %s'
                % (id_, str(args)))
