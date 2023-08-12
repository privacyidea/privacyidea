# -*- coding: utf-8 -*-
#
#  2019-07-02 Friedrich Weber <friedrich.weber@netknights.it>
#             Add a central module for comparing two values
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
"""
This module implements comparisons between two values.
It is tested in test_lib_utils_compare.py

In order to add a new comparator:
 1) add the comparator to COMPARATORS
 2) implement a comparison function and add it to COMPARATOR_FUNCTIONS
 3) add a description of the comparator to COMPARATOR_DESCRIPTIONS
"""
import csv
import logging
import re
from functools import wraps

from privacyidea.lib.framework import _

log = logging.getLogger(__name__)


class CompareError(Exception):
    """
    Signals that an error occurred when carrying out a comparison.
    The error message is not presented to the user, but written to the logfile.
    """
    def __init__(self, message):
        self.message = message

    def __repr__(self):
        return "CompareError({!r})".format(self.message)


def parse_comma_separated_string(input_string):
    """
    Parse a string that contains a list of comma-separated values and return the list of values.
    Each value may be quoted with a doublequote, and doublequotes may be escaped with a backslash.
    Whitespace immediately following a delimiter is skipped.
    Raise a CompareError if the input is malformed.
    :param input_string: an input string
    :return: a list of strings
    """
    # We use Python's csv module because it supports quoted values
    try:
        reader = csv.reader([input_string], strict=True, skipinitialspace=True, doublequote=False, escapechar="\\")
        rows = list(reader)
    except csv.Error as exx:
        raise CompareError("Malformed comma-separated value: {!r}".format(input_string, exx))
    return rows[0]


def _compare_equality(left, comparator, right):
    """
    Return True if two values are exactly equal, according to Python semantics.
    """
    return left == right


def _compare_smaller(left, comparator, right):
    """
    Return True if the left value as integer is smaller than the right integer
    """
    return int(left or 0) < int(right)


def _compare_bigger(left, comparator, right):
    """
    Return True if the left value as integer is bigger than the right integer
    """
    return int(left or 0) > int(right)


def _compare_contains(left, comparator, right):
    """
    Return True if ``left`` has ``right`` as an element.
    Raise a CompareError if ``left`` is not a list.
    :param left: a Python list
    :param right: an arbitrary Python value
    :return: True or False
    """
    if isinstance(left, list):
        return right in left
    else:
        raise CompareError("Left value must be a list, not {!r}".format(type(left)))


def _compare_matches(left, comparator, right):
    """
    Return True if the string in ``left`` completely matches the regular expression given in ``right``.
    Raise a CompareError if ``right`` is not a valid regular expression, or
    if any other matching error occurs.
    :param left: a string
    :param right: a regular expression
    :return: True or False
    """
    try:
        # check for regex modes
        m = re.match(r'^(\(\?[a-zA-Z]+\))(.+)$', right)
        if m and len(m.groups()) == 2:
            regex = m.group(1) + r'^' + m.group(2) + r'$'
        else:
            regex = r"^" + right + r"$"
        return re.match(regex, left) is not None
    except re.error as e:
        raise CompareError("Error during matching: {!r}".format(e))


def _compare_in(left, comparator, right):
    """
    Return True if ``left`` is a member of ``right``, which is a string containing a
    list of values, separated by commas (see ``parse_comma_separated_string``).
    :param left: a string
    :param right: a string of comma-separated values
    :return: True or False
    """
    return left in parse_comma_separated_string(right)


def negate(func):
    """
    Given a comparison function ``func``, build and return a comparison function that negates
    the result of ``func``.
    :param func: a comparison function taking three arguments
    :return: a comparison function taking three arguments
    """
    @wraps(func)
    def negated(left, comparator, right):
        return not func(left, comparator, right)
    return negated


#: This class enumerates all available comparators.
#: In order to add a comparator to this module, add a suitable member to COMPARATORS
#: and suitable entries to COMPARATOR_FUNCTIONS and COMPARATOR_DESCRIPTIONS.
class COMPARATORS(object):
    EQUALS = "equals"
    NOT_EQUALS = "!equals"

    CONTAINS = "contains"
    NOT_CONTAINS = "!contains"

    MATCHES = "matches"
    NOT_MATCHES = "!matches"

    IN = "in"
    NOT_IN = "!in"

    SMALLER = "<"
    BIGGER = ">"


#: This dictionary connects comparators to comparator functions.
#: A comparison function takes three parameters ``left``, ``comparator``, ``right``.
COMPARATOR_FUNCTIONS = {
    COMPARATORS.EQUALS: _compare_equality,
    COMPARATORS.NOT_EQUALS: negate(_compare_equality),

    COMPARATORS.CONTAINS: _compare_contains,
    COMPARATORS.NOT_CONTAINS: negate(_compare_contains),

    COMPARATORS.MATCHES: _compare_matches,
    COMPARATORS.NOT_MATCHES: negate(_compare_matches),

    COMPARATORS.IN: _compare_in,
    COMPARATORS.NOT_IN: negate(_compare_in),

    COMPARATORS.SMALLER: _compare_smaller,
    COMPARATORS.BIGGER: _compare_bigger
}


#: This dictionary connects comparators to their human-readable (and translated) descriptions.
COMPARATOR_DESCRIPTIONS = {
    COMPARATORS.CONTAINS: _("true if the value of the left attribute contains the right value"),
    COMPARATORS.NOT_CONTAINS: _("false if the value of the left attribute contains the right value"),

    COMPARATORS.EQUALS: _("true if the value of the left attribute equals the right value"),
    COMPARATORS.NOT_EQUALS: _("false if the value of the left attribute equals the right value"),

    COMPARATORS.MATCHES: _("true if the value of the left attribute completely matches the given regular expression pattern on the right"),
    COMPARATORS.NOT_MATCHES: _("false if the value of the left attribute completely matches the given regular expression pattern on the right"),

    COMPARATORS.IN: _("true if the value of the left attribute is contained in the comma-separated values on the right"),
    COMPARATORS.NOT_IN: _("false if the value of the left attribute is contained in the comma-separated values on the right"),

    COMPARATORS.SMALLER: _("true if the integer value of the left attribute is smaller than the right integer value"),
    COMPARATORS.BIGGER: _("true if the integer value of the left attribute is bigger than the right integer value")
}


def compare_values(left, comparator, right):
    """
    Compare two values according to ``comparator`` and return either True or False.
    If the comparison is invalid, raise a CompareError with a descriptive message.
    :param left: Left operand of the comparison
    :param comparator: Comparator to use, one of ``COMPARATORS``
    :param right: Right operand of the comparison
    :return: True or False
    """
    if comparator in COMPARATOR_FUNCTIONS:
        return COMPARATOR_FUNCTIONS[comparator](left, comparator, right)
    else:
        raise CompareError("Invalid comparator: {!r}".format(comparator))
