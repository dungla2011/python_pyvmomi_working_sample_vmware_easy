"""
Convenience methods for converting variable names
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import keyword
from re import compile as compile_regex


class Converter(object):
    """
    Convenience methods for converting variable names
    """
    _mixedcase_to_underscore = compile_regex(
        r'(?<=[a-z])[A-Z]|(?<!^)[A-Z](?=[a-z])')
    _underscore_to_mixedcase = compile_regex(r'_([A-Za-z])')

    @staticmethod
    def capitalize(name):
        """
        Capitalize the first letter of the name

        :type  name: :class:`str`
        :param name: name to be converted

        :rtype: :class:`str`
        :return: name with first letter capitalized
        """
        return name[0].upper() + name[1:]

    @staticmethod
    def uncapitalize(name):
        """
        Uncapitalize the first letter of the name

        :type  name: :class:`str`
        :param name: name to be converted

        :rtype: :class:`str`
        :return: name with first letter uncapitalized
        """
        return name[0].lower() + name[1:]

    @staticmethod
    def mixedcase_to_underscore(name):
        """
        Convert from mixedCase to lower_case_with_underscore format

        :type  name: :class:`str`
        :param name: name in mixedCase format

        :rtype: :class:`str`
        :return: name in lower_case_with_underscore format
        """
        return Converter._mixedcase_to_underscore.sub(r"_\g<0>",
                                                      name).lower()

    @staticmethod
    def underscore_to_mixedcase(name):
        """
        Convert from lower_case_with_underscore to mixedCase format

        :type  name: :class:`str`
        :param name: name in lower_case_with_underscore

        :rtype: :class:`str`
        :return: name in mixedCase
        """
        return Converter._underscore_to_mixedcase.sub(lambda m:
                                                      (m.group(1).upper()),
                                                      name)

    @staticmethod
    def capwords_to_underscore(name):
        """
        Convert from CapWords to lower_case_with_underscore format

        :type  name: :class:`str`
        :param name: name in CapWords format

        :rtype: :class:`str`
        :return: name in lower_case_with_underscore format
        """
        return Converter.mixedcase_to_underscore(name)

    @staticmethod
    def underscore_to_capwords(name):
        """
        Convert from lower_case_with_underscore to CapWords format

        :type  name: :class:`str`
        :param name: name in lower_case_with_underscore

        :rtype: :class:`str`
        :return: name in CapWords
        """
        name = Converter.underscore_to_mixedcase(name)
        return Converter.capitalize(name)

    @staticmethod
    def unreserve_name(name):
        """
        Converts the argument if it clashes with a python keyword. If the string
        matches a keyword, adds a trailing underscore, else it returns the same
        string

        :type  name: :class:`str`
        :param name: The string to be converted

        :rtype:  :class:`str`
        :return: The converted string
        """
        if keyword.iskeyword(name) or name in ['self']:
            return '%s_' % name
        else:
            return name

    @staticmethod
    def pepify(name):
        """
        Converts the argument into a name that conforms to PEP8 standard.
        i.e. lower_case_with_underscore

        :type  name: :class:`str`
        :param name: The string to be converted

        :rtype:  :class:`str`
        :return: The converted string
        """
        name = Converter.mixedcase_to_underscore(name)
        return Converter.unreserve_name(name)

    @staticmethod
    def canonical_to_pep(name):
        """
        Converts the argument from vAPI canonical format to PEP8 compliant
        parameter or attribute name

        :type  name: :class:`str`
        :param name: The string to be converted
        :rtype:  :class:`str`
        :return: The converted string
        """
        return Converter.unreserve_name(name.lower())
