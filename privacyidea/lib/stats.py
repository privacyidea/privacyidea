# -*- coding: utf-8 -*-
#
#  2015-07-16 Initial writeup
#  (c) Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
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
__doc__ = """This module reads audit data and can create statistics from
audit data using pandas.

This module is tested in tests/test_lib_stats.py
"""
import logging
from privacyidea.lib.log import log_with
import datetime
import StringIO
log = logging.getLogger(__name__)

try:
    import matplotlib
    MATPLOT_READY = True
except Exception as exx:
    MATPLOT_READY = False
    log.warning("If you want to see statistics you need to install python "
                "matplotlib.")


@log_with(log)
def get_statistics(auditobject, start_time=datetime.datetime.now()
                                         -datetime.timedelta(days=7),
                   end_time=datetime.datetime.now()):
    """
    Create audit statistics and return a JSON object
    The auditobject is passed from the upper level, usually from the REST API
    as g.auditobject.

    :param auditobject: The audit object
    :type auditobject: Audit Object as defined in auditmodules.base.Audit
    :return: JSON
    """
    result = {}
    df = auditobject.get_dataframe(start_time=start_time, end_time=end_time)

    for key in ["serial", "action"]:
        result["%s_plot" % key] = _get_number_of(df, key)

    return result

def _get_number_of(df, key):
    image_uri = "No data"
    output = StringIO.StringIO()
    try:
        series = df[key].value_counts()[:5]
        fig = series.plot(kind="barh").get_figure()
        fig.savefig(output, format="png")
        o_data = output.getvalue()
        output.close()
        image_data = o_data.encode("base64")
        image_uri = 'data:image/png;base64,%s' % image_data
    except Exception as exx:
        log.info(exx)
    return image_uri
