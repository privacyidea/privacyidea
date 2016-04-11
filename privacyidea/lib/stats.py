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
    matplotlib.style.use('ggplot')
    matplotlib.use('Agg')
except Exception as exx:
    MATPLOT_READY = False
    log.warning("If you want to see statistics you need to install python "
                "matplotlib.")

customcmap = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]


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

    # authentication successful/fail per user or serial
    for key in ["user", "serial"]:
        result["validate_{0!s}_plot".format(key)] = _get_success_fail(df, key)

    # get simple usage
    for key in ["serial", "action"]:
        result["{0!s}_plot".format(key)] = _get_number_of(df, key)

    # failed authentication requests
    for key in ["user", "serial"]:
        result["validate_failed_{0!s}_plot".format(key)] = _get_fail(df, key)

    result["admin_plot"] = _get_number_of(df, "action", nums=20)

    return result

def _get_success_fail(df, key):

    try:
        output = StringIO.StringIO()
        series = df[df.action.isin(["POST /validate/check",
                                    "GET /validate/check"])].groupby([key,
                                                                'success']).size().unstack()
        fig = series.plot(kind="bar", stacked=True,
                          legend=True,
                          title="Authentications",
                          grid=True,
                          color=customcmap).get_figure()
        fig.savefig(output, format="png")
        o_data = output.getvalue()
        output.close()
        image_data = o_data.encode("base64")
        image_uri = 'data:image/png;base64,{0!s}'.format(image_data)
    except Exception as exx:
        log.info(exx)
        image_uri = "{0!s}".format(exx)
    return image_uri

def _get_fail(df, key):

    try:
        output = StringIO.StringIO()
        series = df[(df.success==0)
                    & (df.action.isin(["POST /validate/check",
                                       "GET /validate/check"]))][
                     key].value_counts()[:5]

        plot_canvas = matplotlib.pyplot.figure()
        ax = plot_canvas.add_subplot(1,1,1)

        fig = series.plot(ax=ax, kind="bar",
                          colormap="Reds",
                          stacked=False,
                          legend=False,
                          grid=True,
                          title="Failed Authentications").get_figure()
        fig.savefig(output, format="png")
        o_data = output.getvalue()
        output.close()
        image_data = o_data.encode("base64")
        image_uri = 'data:image/png;base64,{0!s}'.format(image_data)
    except Exception as exx:
        log.info(exx)
        image_uri = "{0!s}".format(exx)
    return image_uri



def _get_number_of(df, key, nums=5):
    """
    return a data url image with a single keyed value.
    It plots the "nums" most occurrences of the "key" column in the dataframe.

    :param df: The DataFrame
    :type df: Pandas DataFrame
    :param key: The key, which should be plotted.
    :param count: how many of the most often values should be plotted
    :return: A data url
    """
    output = StringIO.StringIO()
    output.truncate(0)
    try:
        plot_canvas = matplotlib.pyplot.figure()
        ax = plot_canvas.add_subplot(1, 1, 1)

        series = df[key].value_counts()[:nums]
        fig = series.plot(ax=ax, kind="bar", colormap="Blues",
                          legend=False,
                          stacked=False,
                          title="Numbers of {0!s}".format(key),
                          grid=True).get_figure()
        fig.savefig(output, format="png")
        o_data = output.getvalue()
        output.close()
        image_data = o_data.encode("base64")
        image_uri = 'data:image/png;base64,{0!s}'.format(image_data)
    except Exception as exx:
        log.info(exx)
        image_uri = "No data"
    return image_uri
