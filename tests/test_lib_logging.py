# SPDX-FileCopyrightText: (C) 2025 NetKnights GmbH <https://netknights.it>
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
# SPDX-License-Identifier: AGPL-3.0-or-later
#
import logging
import logging.config

from privacyidea.lib.log import DEFAULT_LOGGING_CONFIG, SecureFormatter
from privacyidea.lib.utils import parse_date


def _record(msg, args=(), **extra):
    record = logging.LogRecord("test", logging.INFO, "some_file.py", 1, msg, args, None)
    record.__dict__.update(extra)
    return record


def test_log_formatter_non_string_message():
    # A log call may pass any object as the message, e.g. log.info(exception)
    formatter = SecureFormatter("%(message)s")
    assert (formatter.format(_record(ValueError("boom\0bad")))
            == "!!Log Entry Secured by SecureFormatter!! boom.bad")
    # The caller location is appended to a non-string message as well
    assert formatter.format(_record(RuntimeError("failed"), s_line=42)) == "failed (called from some_file.py:1)"
    # A format string with arguments is still interpolated
    assert formatter.format(_record("value is %s", ("x",))) == "value is x"


def test_log_formatter(caplog, tmp_path):
    # Test that the secure formatter filters out potentially harmful characters
    DEFAULT_LOGGING_CONFIG["handlers"]["file"]["filename"] = tmp_path.joinpath("test.log").as_posix()
    logging.config.dictConfig(DEFAULT_LOGGING_CONFIG)
    caplog.set_level(logging.DEBUG, logger="privacyidea")
    assert parse_date("2016/\0x052/20") is None
    assert ("!!Log Entry Secured by SecureFormatter!! Dateformat 2016/.x052/20 "
            "could not be parsed") == caplog.messages[0]

