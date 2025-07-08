# (c) NetKnights GmbH 2025,  https://netknights.it
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-FileCopyrightText: 2019 Friedrich Weber <friedrich.weber@netknights.it>
# SPDX-FileCopyrightText: 2025 Jelina Unger <jelina.unger@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
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
import datetime
import logging
import re
from functools import wraps
from typing import Union

from privacyidea.lib.framework import _
from privacyidea.lib.utils import parse_timedelta

log = logging.getLogger(__name__)


class CompareError(Exception):
    """
    Signals that an error occurred when carrying out a comparison.
    The error message is not presented to the user, but written to the logfile.
    """

    def __init__(self, message: str):
        self.message = message

    def __repr__(self):
        return f"CompareError({self.message!r})"


#: This class enumerates all available comparators.
#: In order to add a comparator to this module, add a suitable member to COMPARATORS
#: and suitable entries to COMPARATOR_FUNCTIONS and COMPARATOR_DESCRIPTIONS.
class Comparators():
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

    DATE_BEFORE = "date_before"
    DATE_AFTER = "date_after"

    DATE_WITHIN_LAST = "date_within_last"
    DATE_NOT_WITHIN_LAST = "!date_within_last"

    STRING_CONTAINS = "string_contains"
    STRING_NOT_CONTAINS = "!string_contains"

    @classmethod
    def get_all_comparators(cls) -> list[str]:
        """
        Return a list of all comparators.
        """
        return [cls.EQUALS, cls.NOT_EQUALS, cls.CONTAINS, cls.NOT_CONTAINS, cls.MATCHES, cls.NOT_MATCHES,
                cls.IN, cls.NOT_IN, cls.SMALLER, cls.BIGGER, cls.STRING_CONTAINS, cls.STRING_NOT_CONTAINS,
                cls.DATE_BEFORE, cls.DATE_AFTER, cls.DATE_WITHIN_LAST, cls.DATE_NOT_WITHIN_LAST]


def parse_comma_separated_string(input_string: str) -> list[str]:
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


def _get_datetime(date_time: Union[str, datetime.datetime]) -> datetime.datetime:
    """
    Convert a string in ISO format to a datetime object.
    If the input is already a datetime object, return it unchanged.

    :param date_time: a string in ISO format or a datetime object
    :return: a datetime object
    """
    if isinstance(date_time, str):
        try:
            date_time = datetime.datetime.fromisoformat(date_time)
        except ValueError as error:
            log.error(f"Invalid date format '{date_time}': {error}")
            raise CompareError(f"Invalid date format: {date_time!r}. Expected ISO format.")
    if not isinstance(date_time, datetime.datetime):
        raise CompareError(f"Expected a datetime object or a string in ISO format, got {type(date_time).__name__}")
    return date_time


def _compare_date_before(left: Union[str, datetime.datetime], comparator: str,
                         right: Union[str, datetime.datetime]) -> bool:
    """
    Checks if the left date and time is before the right date and time.
    If the left or the right value are given as strings, they are converted to datetime objects.

    :param left: a datetime object or a string in ISO format
    :param comparator: a comparator, should be Comparators.DATE_BEFORE
    :param right: a datetime object or a string in ISO format
    :return: True if left is before right, False otherwise
    """
    # Convert to datetime objects
    left = _get_datetime(left)
    right = _get_datetime(right)
    if (left.tzinfo is None) ^ (right.tzinfo is None):
        log.error(f"Either both dates must have a timezone or neither of them.")
        raise CompareError("Cannot compare timezone-naive and timezone-aware datetimes.")
    return left < right


def _compare_date_after(left: Union[str, datetime.datetime], comparator: str,
                        right: Union[str, datetime.datetime]) -> bool:
    """
    Checks if the left date and time is after the right date and time.
    If the left or the right value are given as strings, they are converted to datetime objects.

    :param left: a datetime object or a string in ISO format
    :param comparator: a comparator, should be Comparators.DATE_AFTER
    :param right: a datetime object or a string in ISO format
    :return: True if left is after right, False otherwise
    """
    # Convert to datetime objects
    left = _get_datetime(left)
    right = _get_datetime(right)
    if (left.tzinfo is None) ^ (right.tzinfo is None):
        log.error(f"Either both dates must have a timezone or neither of them.")
        raise CompareError("Cannot compare timezone-naive and timezone-aware datetimes.")
    return left > right


def _compare_date_within_last(date_to_check: Union[str, datetime.datetime], comparator: str,
                              time_delta: str) -> bool:
    """
    Checks if the date and time is within the past duration specified by the time_delta.

    :param date_to_check: a datetime object or a string in ISO format
    :param comparator: a comparator, should be Comparators.DATE_WITHIN_LAST
    :param time_delta: a string representing a time delta / duration (e.g., '1y', '7d', '6h', '15m')
    :return: True if the left date is within the past duration, False otherwise
    """
    date_to_check = _get_datetime(date_to_check)
    if date_to_check.tzinfo is None:
        log.debug("Date to check is timezone-naive, assuming UTC.")
        date_to_check = date_to_check.replace(tzinfo=datetime.timezone.utc)
    try:
        condition_time_delta = parse_timedelta(time_delta)
    except TypeError as error:
        raise CompareError(str(error))

    # calculate the true time difference between the time stamp and now
    now = datetime.datetime.now(datetime.timezone.utc)
    true_time_delta = now - date_to_check

    # compare the true time value with the condition time value
    return true_time_delta < condition_time_delta


def _compare_string_contains(text: str, comparator: str, substring: str) -> bool:
    """
    Checks if the text contains the substring.

    :param text: a string to check
    :param comparator: a comparator, should be Comparators.STRING_CONTAINS
    :param substring: a substring to look for in the text
    :return: True if the text contains the substring, False otherwise
    """
    if not isinstance(text, str) or not isinstance(substring, str):
        raise CompareError(f"Expected a string, got {type(text).__name__}")
    return substring.lower() in text.lower()


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


#: This dictionary connects comparators to comparator functions.
#: A comparison function takes three parameters ``left``, ``comparator``, ``right``.
COMPARATOR_FUNCTIONS = {
    Comparators.EQUALS: _compare_equality,
    Comparators.NOT_EQUALS: negate(_compare_equality),

    Comparators.CONTAINS: _compare_contains,
    Comparators.NOT_CONTAINS: negate(_compare_contains),

    Comparators.MATCHES: _compare_matches,
    Comparators.NOT_MATCHES: negate(_compare_matches),

    Comparators.IN: _compare_in,
    Comparators.NOT_IN: negate(_compare_in),

    Comparators.SMALLER: _compare_smaller,
    Comparators.BIGGER: _compare_bigger,

    Comparators.DATE_BEFORE: _compare_date_before,
    Comparators.DATE_AFTER: _compare_date_after,

    Comparators.DATE_WITHIN_LAST: _compare_date_within_last,
    Comparators.DATE_NOT_WITHIN_LAST: negate(_compare_date_within_last),

    Comparators.STRING_CONTAINS: _compare_string_contains,
    Comparators.STRING_NOT_CONTAINS: negate(_compare_string_contains)

}

#: This dictionary connects comparators to their human-readable (and translated) descriptions.
COMPARATOR_DESCRIPTIONS = {
    Comparators.CONTAINS: _("True if the value of the left attribute contains the right value"),
    Comparators.NOT_CONTAINS: _("False if the value of the left attribute contains the right value"),

    Comparators.EQUALS: _("True if the value of the left attribute equals the right value"),
    Comparators.NOT_EQUALS: _("False if the value of the left attribute equals the right value"),

    Comparators.MATCHES: _("True if the value of the left attribute completely matches the given regular expression "
                           "pattern on the right"),
    Comparators.NOT_MATCHES: _("False if the value of the left attribute completely matches the given regular "
                               "expression pattern on the right"),

    Comparators.IN: _("True if the value of the left attribute is contained in the comma-separated values on the "
                      "right"),
    Comparators.NOT_IN: _("False if the value of the left attribute is contained in the comma-separated values on the "
                          "right"),

    Comparators.SMALLER: _("True if the integer value of the left attribute is smaller than the right integer value"),
    Comparators.BIGGER: _("True if the integer value of the left attribute is bigger than the right integer value"),

    Comparators.DATE_BEFORE: _("True if the date and time of the left attribute is before the date and time of the "
                               "right attribute"),
    Comparators.DATE_AFTER: _("True if the date and time of the left attribute is after the date and time of the "
                              "right attribute"),
    Comparators.DATE_WITHIN_LAST: _("True if the date and time of the left attribute is within the past duration of "
                                    "the right attribute. The right attribute should be a duration such as '1y', '7d', "
                                    "'6h', '15m'."),
    Comparators.DATE_NOT_WITHIN_LAST: _("False if the date and time of the left attribute is within the past duration "
                                        "of the right attribute. The right attribute should be a duration such as "
                                        "'1y', '7d', '6h', '15m'."),
    Comparators.STRING_CONTAINS: _(
        "True if the value of the left attribute contains the right value (case-insensitive)"),
    Comparators.STRING_NOT_CONTAINS: _(
        "False if the value of the left attribute contains the right value (case-insensitive)"),
}


def compare_values(left, comparator: str, right) -> bool:
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
        raise CompareError(f"Invalid comparator: {comparator!r}")
