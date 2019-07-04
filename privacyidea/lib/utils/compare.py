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
"""

import logging
log = logging.getLogger(__name__)


class CompareError(Exception):
    def __init__(self, message):
        self.message = message


def _compare_equality(left, comparator, right):
    """
    Return True if two values are exactly equal, according to Python semantics.
    """
    return left == right


def _compare_contains(left, comparator, right):
    """
    Return True if ``left`` has ``right`` as an element. Raise a CompareError if
    ``left`` is not a list.
    """
    if isinstance(left, list):
        return right in left
    else:
        raise CompareError(u"Left value must be a list, not {!r}".format(type(left)))


COMPARATORS = {
    "==": _compare_equality,
    "contains": _compare_contains,
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
    if comparator in COMPARATORS:
        return COMPARATORS[comparator](left, comparator, right)
    else:
        # We intentionally leave out the values, in case sensitive values are compared
        raise CompareError(u"Invalid comparator: {!r}".format(comparator))


__all__ = [COMPARATORS, compare_values]
