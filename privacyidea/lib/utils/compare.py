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
from dataclasses import dataclass
from functools import wraps
from typing import Union, Optional

from dateutil.parser import parse, isoparse

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


def _parse_int(value: Union[str, int]) -> int:
    """
    Parse a value as an integer.
    If the value cannot be parsed as an integer, raise a CompareError.

    :param value: value to be parsed to an integer
    :return: value as integer
    """
    if isinstance(value, int):
        return value
    try:
        int_value = int(value)
    except ValueError:
        raise CompareError(f"Cannot convert value '{value}' to integer.")
    return int_value


def _compare_equality(left: any, right: any) -> bool:
    """
    Return True if two values are exactly equal, according to Python semantics.
    """
    return left == right


def _compare_smaller(left: Union[int, str], right: Union[int, str]) -> bool:
    """
    Return True if the left value as integer is smaller than the right integer
    """
    left = _parse_int(left or 0)
    right = _parse_int(right)
    return left < right


def _compare_smaller_any(left: any, right: any) -> bool:
    """
    Return True if the left value is smaller than the right value. Any type of value is allowed.
    """
    return left < right


def _compare_less_equal(left: Union[str, int], right: Union[str, int]) -> bool:
    """
    Return True if the left value as integer is smaller or equal to the right integer
    """
    left = _parse_int(left or 0)
    right = _parse_int(right)
    return left <= right


def _compare_bigger(left: Union[int, str], right: Union[int, str]) -> bool:
    """
    Return True if the left value as integer is bigger than the right integer
    """
    left = _parse_int(left or 0)
    right = _parse_int(right)
    return left > right


def _compare_bigger_any(left: any, right: any) -> bool:
    """
    Return True if the left value is bigger than the right value. Any type of value is allowed.
    """
    return left > right


def _compare_greater_equal(left: Union[str, int], right: Union[str, int]) -> bool:
    """
    Return True if the left value as integer is bigger or equal to the right integer
    """
    left = _parse_int(left or 0)
    right = _parse_int(right)
    return left >= right


def _compare_contains(left: list, right: any) -> bool:
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
        raise CompareError(f"Left value must be a list, not {type(left)}")


def _compare_matches(left: str, right: str) -> bool:
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


def _compare_in(left: str, right: str) -> bool:
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
    Convert a string in ISO format to a datetime object. Low precision dates are not supported. The date string must
    at least have the format 'YYYY-MM-DD'.
    If the input is already a datetime object, return it unchanged.
    If the date_time string is not a valid iso format, a CompareError is raised.

    :param date_time: a string in ISO format or a datetime object
    :return: a datetime object
    """
    if isinstance(date_time, str):
        try:
            # Beginning with python 3.11 we could also use `datetime.datetime.fromisoformat(date_time)`, but in
            # python 3.9 and 3.10 some formats are not supported.
            if len(date_time) < 10:
                # Avoid guessing the month and day, at least YYYY-MM-DD is required
                raise ValueError("Low precision date strings are not supported!")
            # Parse the string into a datetime object
            date_time = isoparse(date_time)
        except ValueError as error:
            log.error(f"Invalid date format '{date_time}': {error}")
            raise CompareError(f"Invalid date format: {date_time!r}. Expected ISO format.")
    if not isinstance(date_time, datetime.datetime):
        raise CompareError(f"Expected a datetime object or a string in ISO format, got {type(date_time).__name__}")
    return date_time


def _compare_date_before(left: Union[str, datetime.datetime], right: Union[str, datetime.datetime]) -> bool:
    """
    Checks if the left date and time is before the right date and time.
    If the left or the right value are given as strings, they are converted to datetime objects.

    :param left: a datetime object or a string in ISO format
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


def _compare_date_after(left: Union[str, datetime.datetime], right: Union[str, datetime.datetime]) -> bool:
    """
    Checks if the left date and time is after the right date and time.
    If the left or the right value are given as strings, they are converted to datetime objects.

    :param left: a datetime object or a string in ISO format
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


def _compare_date_within_last(date_to_check: Union[str, datetime.datetime], time_delta: str) -> bool:
    """
    Checks if the date and time is within the past duration specified by the time_delta.

    :param date_to_check: a datetime object or a string in ISO format
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


def _compare_string_contains(text: str, substring: str) -> bool:
    """
    Checks if the text contains the substring.

    :param text: a string to check
    :param substring: a substring to look for in the text
    :return: True if the text contains the substring, False otherwise
    """
    if not isinstance(text, str) or not isinstance(substring, str):
        raise CompareError(f"Expected a string, got {type(text).__name__}")
    return substring.lower() in text.lower()


def negate(func: callable) -> callable:
    """
    Given a comparison function ``func``, build and return a comparison function that negates
    the result of ``func``.

    :param func: a comparison function taking the two values to compare as arguments
    :return: a comparison function taking the two values to compare as arguments
    """
    @wraps(func)
    def negated(left: any, right: any) -> bool:
        return not func(left, right)

    return negated

# In order to add a comparator to this module, add a suitable member to PrimaryComparators and add an entry in the
# COMPARATORS dictionary to map the name to the corresponding Comparator object containing the related function and
# description.

# This class enumerates all available primary comparators. For some of them also other names are accepted, but
# these are the preferred names which are used internally. Additionally, only these are used to generate the
# COMPARATOR_DESCRIPTIONS dictionary.
class PrimaryComparators:
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
        Return a list of all primary comparators.
        """
        return [v for k, v in vars(cls).items() if k.isupper()]

    @classmethod
    def get_all_int_comparators(cls) -> list[str]:
        """
        Return a list of all primary comparators that can be used for integer comparisons.
        """
        return [cls.EQUALS, cls.NOT_EQUALS, cls.SMALLER, cls.BIGGER]


@dataclass
class Comparator:
    name: str
    function: callable
    # description only for primary comparators to be displayed in the UI
    description: str
    # Whether the comparator function only accepts specific types of the values and handles the type conversion
    type_restricted: bool = False


# Comparator objects
equals = Comparator(PrimaryComparators.EQUALS, _compare_equality,
                    _("True if the value of the left attribute is equal to the right value"))
not_equals = Comparator(PrimaryComparators.NOT_EQUALS, negate(_compare_equality),
                        _("False if the value of the left attribute is equal to the right value"))
contains = Comparator(PrimaryComparators.CONTAINS, _compare_contains,
                      _("True if the list of the left attribute contains the right value"), True)
not_contains = Comparator(PrimaryComparators.NOT_CONTAINS, negate(_compare_contains),
                          _("False if the list of the left attribute contains the right value"), True)
matches = Comparator(PrimaryComparators.MATCHES, _compare_matches,
                     _("True if the value of the left attribute completely matches the given regular expression "
                       "pattern on the right"), True)
not_matches = Comparator(PrimaryComparators.NOT_MATCHES, negate(_compare_matches),
                         _("False if the value of the left attribute completely matches the given regular expression "
                           "pattern on the right"), True)
in_ = Comparator(PrimaryComparators.IN, _compare_in,
                 _("True if the value of the left attribute is contained in the comma-separated list on the right"),
                 True)
not_in = Comparator(PrimaryComparators.NOT_IN, negate(_compare_in),
                    _("False if the value of the left attribute is contained in the comma-separated list on the right"),
                    True)
smaller = Comparator(PrimaryComparators.SMALLER, _compare_smaller,
                     _("True if the integer value of the left attribute is smaller than the right integer value"),
                     True)
smaller_any = Comparator("<_any", _compare_smaller_any, "")
less_equal = Comparator("<=", _compare_less_equal, "", True)
bigger = Comparator(PrimaryComparators.BIGGER, _compare_bigger,
                    _("True if the integer value of the left attribute is bigger than the right integer value"), True)
bigger_any = Comparator(">_any", _compare_bigger_any, "")
greater_equal = Comparator(">=", _compare_greater_equal, "", True)
date_before = Comparator(PrimaryComparators.DATE_BEFORE, _compare_date_before,
                         _("True if the date and time of the left attribute is before the date and time of the right "
                           "attribute"), True)
date_after = Comparator(PrimaryComparators.DATE_AFTER, _compare_date_after,
                        _("True if the date and time of the left attribute is after the date and time of the right "
                          "attribute"), True)
date_within_last = Comparator(PrimaryComparators.DATE_WITHIN_LAST, _compare_date_within_last,
                              _("True if the date and time of the left attribute is within the past duration of the "
                                "right attribute. The right attribute should be a duration such as '1y', '7d', '6h', "
                                "'15m'."), True)
date_not_within_last = Comparator(PrimaryComparators.DATE_NOT_WITHIN_LAST, negate(_compare_date_within_last),
                                  _("False if the date and time of the left attribute is within the past duration of "
                                    "the right attribute. The right attribute should be a duration such as '1y', '7d', "
                                    "'6h', '15m'."), True)
string_contains = Comparator(PrimaryComparators.STRING_CONTAINS, _compare_string_contains,
                             _("True if the value of the left attribute contains the right value (case-insensitive)"),
                             True)
string_not_contains = Comparator(PrimaryComparators.STRING_NOT_CONTAINS, negate(_compare_string_contains),
                                 _("False if the value of the left attribute contains the right value "
                                   "(case-insensitive)"), True)

# Map different comparator names to the corresponding Comparator objects.
COMPARATORS = {PrimaryComparators.EQUALS: equals, "=": equals, "==": equals, "==_any": equals, "=_any": equals,
               PrimaryComparators.NOT_EQUALS: not_equals, "!=": not_equals, "!=_any": not_equals,
               PrimaryComparators.CONTAINS: contains,
               PrimaryComparators.NOT_CONTAINS: not_contains,
               PrimaryComparators.MATCHES: matches,
               PrimaryComparators.NOT_MATCHES: not_matches,
               PrimaryComparators.IN: in_,
               PrimaryComparators.NOT_IN: not_in,
               PrimaryComparators.SMALLER: smaller, "<_any": smaller_any,
               "<=": less_equal, "=<": less_equal,
               PrimaryComparators.BIGGER: bigger, ">_any": bigger_any,
               ">=": greater_equal, "=>": greater_equal,
               PrimaryComparators.DATE_BEFORE: date_before,
               PrimaryComparators.DATE_AFTER: date_after,
               PrimaryComparators.DATE_WITHIN_LAST: date_within_last,
               PrimaryComparators.DATE_NOT_WITHIN_LAST: date_not_within_last,
               PrimaryComparators.STRING_CONTAINS: string_contains,
               PrimaryComparators.STRING_NOT_CONTAINS: string_not_contains}

# This dictionary connects comparators to their human-readable (and translated) descriptions.
COMPARATOR_DESCRIPTIONS = {comparator: COMPARATORS[comparator].description for comparator in
                           PrimaryComparators.get_all_comparators()}

def get_all_type_restricted_comparators() -> list[str]:
    """
    Return a list of all type-restricted comparators.
    Type-restricted comparators are those that only work with specific data types, such as integers or strings.
    The type conversion is done automatically by the compare function.
    """
    return [comparator.name for comparator in COMPARATORS.values() if comparator.type_restricted]


def compare_values(left, comparator_name: str, right) -> bool:
    """
    Compare two values according to ``comparator`` and return either True or False.
    If the comparison is invalid, raise a CompareError with a descriptive message.

    :param left: Left operand of the comparison
    :param comparator_name: Comparator to use
    :param right: Right operand of the comparison
    :return: True or False
    """
    comparator = COMPARATORS.get(comparator_name)
    if not comparator:
        raise CompareError(f"Invalid comparator: {comparator_name!r}")
    return comparator.function(left, right)


def compare_time(condition: str, time_value: Union[datetime.datetime, str]) -> bool:
    """
    Evaluates whether a passed timestamp is within a certain time frame in the past compared to now.
    In case of a CompareError, the error is logged and False is returned.

    :param condition: The maximum time difference the time value may have to now, e.g. "5d", "2h", "30m"
                 The following units are supported: y (years), d (days), h (hours), m (minutes), s (seconds)
    :param time_value: The timestamp to be compared to now
    :return: True if the time difference between the time stamp and now is less than the condition value,
             False otherwise
    """
    try:
        result = compare_values(time_value, PrimaryComparators.DATE_WITHIN_LAST, condition)
    except CompareError as error:
        log.debug(
            f"Error during time comparison for condition '{condition}' and date time value '{time_value}': {error}")
        return False
    return result


@dataclass
class Condition:
    left_value: str
    comparator: str
    right_value: str


def parse_condition(condition: str, data_type: Optional[str] = None) -> Union[Condition, None]:
    """
    Extracts the comparator and the condition values from a condition string.
    The condition can have the following structures:
        * "value comparator value", e.g. "registration_state == 'registered'"
        * "comparator value", e.g. "<1000"
        * "value", e.g. "123" (interpreted as "== 123")

    :param condition: A string like <100
    :param data_type: The expected datatype of the values to only check for valid comparators
    :return: A Condition object with comparator and values or None in case of an empty condition string.
    """
    condition = condition.strip()
    if not condition:
        # No condition to match!
        log.debug("Empty condition provided.")
        return None

    # For consistency all comparators should be quoted, but we also need to support the old unquoted comparators
    if data_type == "int":
        # Only check for comparators that can handle integers
        primary_comparators = [f"'{comparator}'" for comparator in PrimaryComparators.get_all_int_comparators()]
    else:
        primary_comparators = [f"'{comparator}'" for comparator in PrimaryComparators.get_all_comparators()]
    basic_comparators = ["==", "!=", "<=", "=<", ">=", "=>", "<", ">", "="]
    basic_quoted_comparators = [f"'{comparator}'" for comparator in basic_comparators]
    allowed_comparators = primary_comparators + basic_quoted_comparators + basic_comparators
    for tmp_comparator in allowed_comparators:
        values = condition.split(tmp_comparator)
        if len(values) == 2:
            left_value, right_value = [x.strip() for x in values]

            if tmp_comparator.startswith("'") and tmp_comparator.endswith("'"):
                # remove quotes
                comparator = tmp_comparator[1:-1]
            else:
                comparator = tmp_comparator
            return Condition(left_value, comparator, right_value)
    # No comparator found, so we assume it is an equals comparator and the full condition is the right value
    return Condition("", PrimaryComparators.EQUALS, condition.strip())


def compare_ints(condition: str, value: Union[str, int]) -> bool:
    """
    This function first extracts the comparator and the right-hand side value from the condition,
    and then performs the comparison. Both values are expected to be parsable as integers.

    The condition can start with '<', '==', '!=' or '>' and contain a number like:
    <100
    >1000
    ==123
    123 is interpreted as ==123

    :param condition: A condition as string like "<100"
    :param value: the value to check
    :return: True if condition is true, False otherwise and on any error
    """
    condition = parse_condition(condition, data_type="int")
    if not condition:
        return False

    # convert both values to int
    try:
        value = int(value)
        condition_value = int(condition.right_value)
    except ValueError:
        log.debug(f"Cannot convert values to integers: condition value '{condition.right_value}', value '{value}'")
        return False

    # Compare the values, but fail silent
    try:
        result = compare_values(value, condition.comparator, condition_value)
    except CompareError as error: # pragma no cover
        log.debug(f"Error during comparison: {error}")
        return False
    return result


def compare_generic(condition: str, key_method: callable, warning: str) -> bool:
    """
    Compares a condition like "tokeninfoattribute == value".
    It uses the "key_method" to determine the value of "tokeninfoattribute".

    If the value does not match or the key does not exist, it returns False.

    :param condition: A condition containing a comparator like "==", ">", "<"
    :param key_method: A function call, that get the value from the key
    :param warning: A warning message to be written to the log file in case the condition is not parsable.
    :return: True or False
    """
    condition = parse_condition(condition)
    if not condition:
        # No condition to match!
        return False

    key = condition.left_value
    comparator = condition.comparator
    right_value = condition.right_value
    if right_value is None or not key or not comparator:
        # There is a condition, but we do not know it!
        log.warning(warning.format(condition))
        return False

    left_value = key_method(key)
    if left_value is None:
        log.debug(f"Key {key} not found.")
        return False

    # We do not know the type, hence we use the generic comparison without type conversion in the comparator function
    if comparator in ["<", ">"]:
        comparator += "_any"

    # Datatype conversion
    if comparator not in get_all_type_restricted_comparators():
        # A comparator without explicit type restriction, so we try to convert both values
        # Try to convert to ints
        try:
            int1 = int(left_value)
            int2 = int(right_value)
            # We only converts BOTH values if possible
            left_value = int1
            right_value = int2
        except Exception:
            log.debug(f"Convert '{left_value}' and/or '{right_value}' to integers failed.")

        if not isinstance(left_value, int) and not isinstance(right_value, int):
            # try to convert both values to a timestamp
            try:
                date1 = parse(left_value)
                date2 = parse(right_value)
                if date1 and date2:
                    # Only use dates, if both values can be converted to dates
                    left_value = date1
                    right_value = date2
            except Exception:
                log.debug(f"Convert '{left_value}' or '{right_value}' to datetime objects failed.")

    # Compare the values, but fail silent
    try:
        # append "_any" to the comparator to indicate that we want to compare any type of value
        result = compare_values(left_value, comparator, right_value)
    except CompareError as error:   # pragma no cover
        log.debug(f"Error during comparison: {error}")
        return False

    log.debug(f"Comparing {key} {comparator} {right_value} with result {result}.")
    return result
