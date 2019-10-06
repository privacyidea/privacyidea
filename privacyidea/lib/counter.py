# -*- coding: utf-8 -*-
#
#  2018-26-09 Paul Lettich <paul.lettich@netknights.it>
#             Add decrease/reset functions
#  2018-03-01 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#
#  Copyright (C) 2018 Cornelius Kölbel
#  License:  AGPLv3
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
"""
This module is used to modify counters in the database
"""
from sqlalchemy import func

from privacyidea.lib.config import get_privacyidea_node
from privacyidea.models import EventCounter, db


def increase(counter_name):
    """
    Increase the counter value in the database.
    If the counter does not exist yet, create the counter.

    :param counter_name: The name/identifier of the counter
    :return: None
    """
    # If there is no table row for the current node, create one.
    node = get_privacyidea_node()
    counter = EventCounter.query.filter_by(counter_name=counter_name, node=node).first()
    if not counter:
        counter = EventCounter(counter_name, 0, node=node)
        counter.save()
    counter.increase()


def _reset_counter_on_all_nodes(counter_name):
    """
    Reset all EventCounter rows that set a value for ``counter_name`` to zero,
    regardless of the node column.
    :param counter_name:  The name/identifier of the counter
    """
    EventCounter.query.filter_by(counter_name=counter_name).update({'counter_value': 0})
    db.session.commit()


def decrease(counter_name, allow_negative=False):
    """
    Decrease the counter value in the database.
    If the counter does not exist yet, create the counter.
    Also checks whether the counter is allowed to become negative.

    :param counter_name: The name/identifier of the counter
    :param allow_negative: Whether the counter can become negative. Note that even if this flag is not set,
                           the counter may become negative due to concurrent queries.
    :return: None
    """
    node = get_privacyidea_node()
    counter = EventCounter.query.filter_by(counter_name=counter_name, node=node).first()
    if not counter:
        counter = EventCounter(counter_name, 0, node=node)
        counter.save()
    # We are allowed to decrease the current counter object only if the overall
    # counter value is positive (because individual rows may be negative then),
    # or if we allow negative values. Otherwise, we need to reset all rows of all nodes.
    if read(counter_name) > 0 or allow_negative:
        counter.decrease()
    else:
        _reset_counter_on_all_nodes(counter_name)


def reset(counter_name):
    """
    Reset the counter value in the database to 0.
    If the counter does not exist yet, create the counter.
    :param counter_name: The name/identifier of the counter
    :return:
    """
    node = get_privacyidea_node()
    counters = EventCounter.query.filter_by(counter_name=counter_name).count()
    if not counters:
        counter = EventCounter(counter_name, 0, node=node)
        counter.save()
    else:
        _reset_counter_on_all_nodes(counter_name)


def read(counter_name):
    """
    Read the counter value from the database.
    If the counter_name does not exist, 'None' is returned.

    :param counter_name: The name of the counter
    :return: The value of the counter
    """
    return db.session.query(func.sum(EventCounter.counter_value))\
        .filter(EventCounter.counter_name == counter_name).one()[0]
