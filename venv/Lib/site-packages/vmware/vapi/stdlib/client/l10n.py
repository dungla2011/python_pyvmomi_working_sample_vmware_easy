"""
Helper classes for client side localization.
"""
__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


from vmware.vapi.l10n.formatter import StringFormatter


class MessageLocalizer(object):
    """
    Helper class to localize vAPI LocalizableMessages.

    Before initializating the MessageLocalizer, locale
    has to be explicitly set if the user wants a locale
    other than English (U.S.).

    Typically, at the start of the application, the following
    two lines are required to set the locale.

    import locale
    locale.setlocale(locale.LC_ALL,<locale_type>)

    If the locale_type is empty string, locale is set to user's
    default setting (typically specified in the LANG environment
    variable). Otherwise, the specified locale type has to be
    installed in the system.
    """
    def __init__(self, bundle, formatter=StringFormatter):
        """
        Initialize MessageLocalizer

        :type  bundle: :class:`vmware.vapi.message.MessageBundle`
        :param bundle: Message bundle to retrieve the templates for the
            messages
        :type  formatter: :class:`vmware.vapi.message.MessageFormatter`
        :param formatter: Message formatter to format the messages
        """
        self._bundle = bundle
        self._formatter = formatter

    def localize(self, msg):
        """
        Localize a given LocalizableMessage.

        :type  msg: :class:`com.vmware.vapi.std_client.LocalizableMessage`
        :param msg: LocalizableMessage
        :rtype: :class:`str`
        :return: Localized string
        """
        try:
            template = self._bundle.get(msg.id)
        except KeyError:
            raise Exception('Invalid message identifier: %s' % msg.id)
        return self._formatter.format_msg(template, msg.args)
