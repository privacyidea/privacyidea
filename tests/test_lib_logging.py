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

from privacyidea.lib.log import DEFAULT_LOGGING_CONFIG, _hide_nested_keys, log_with
from privacyidea.lib.utils import parse_date


def test_log_formatter(caplog, tmp_path):
    # Test that the secure formatter filters out potentially harmful characters
    DEFAULT_LOGGING_CONFIG["handlers"]["file"]["filename"] = tmp_path.joinpath("test.log").as_posix()
    logging.config.dictConfig(DEFAULT_LOGGING_CONFIG)
    caplog.set_level(logging.DEBUG, logger="privacyidea")
    assert parse_date("2016/\0x052/20") is None
    assert ("!!Log Entry Secured by SecureFormatter!! Dateformat 2016/.x052/20 "
            "could not be parsed") == caplog.messages[0]


class TestHideNestedKeys:
    """Tests for the _hide_nested_keys helper function."""

    def test_hide_top_level_key(self):
        data = {"pin": "1234", "user": "admin"}
        _hide_nested_keys(data, ["pin"])
        assert data == {"pin": "HIDDEN", "user": "admin"}

    def test_hide_nested_key(self):
        data = {"user": {"pin": "secret", "name": "admin"}, "type": "hotp"}
        _hide_nested_keys(data, ["pin"])
        assert data == {"user": {"pin": "HIDDEN", "name": "admin"}, "type": "hotp"}

    def test_hide_deeply_nested_key(self):
        data = {"level1": {"level2": {"level3": {"password": "secret"}}}}
        _hide_nested_keys(data, ["password"])
        assert data == {"level1": {"level2": {"level3": {"password": "HIDDEN"}}}}

    def test_hide_multiple_keys(self):
        data = {"pin": "1234", "otpkey": "abcdef", "type": "hotp"}
        _hide_nested_keys(data, ["pin", "otpkey"])
        assert data == {"pin": "HIDDEN", "otpkey": "HIDDEN", "type": "hotp"}

    def test_hide_key_in_list_of_dicts(self):
        data = {"users": [{"name": "alice", "pin": "1111"}, {"name": "bob", "pin": "2222"}]}
        _hide_nested_keys(data, ["pin"])
        assert data == {"users": [{"name": "alice", "pin": "HIDDEN"}, {"name": "bob", "pin": "HIDDEN"}]}

    def test_hide_key_at_multiple_levels(self):
        data = {"pin": "top", "nested": {"pin": "deep"}}
        _hide_nested_keys(data, ["pin"])
        assert data == {"pin": "HIDDEN", "nested": {"pin": "HIDDEN"}}

    def test_no_matching_keys(self):
        data = {"user": "admin", "type": "hotp"}
        _hide_nested_keys(data, ["pin"])
        assert data == {"user": "admin", "type": "hotp"}

    def test_empty_dict(self):
        data = {}
        _hide_nested_keys(data, ["pin"])
        assert data == {}

    def test_non_dict_data(self):
        # Should not raise on non-dict data
        data = "just a string"
        _hide_nested_keys(data, ["pin"])  # no-op, no error


class TestLogWithHideArgsKeywords:
    """Tests for the log_with decorator with hide_args_keywords on nested dicts."""

    def test_hide_args_keywords_top_level(self, caplog):
        logger = logging.getLogger("privacyidea.test.log_with")
        logger.setLevel(logging.DEBUG)

        @log_with(logger, hide_args_keywords={0: ["pin"]})
        def my_func(param):
            return "ok"

        with caplog.at_level(logging.DEBUG, logger="privacyidea.test.log_with"):
            result = my_func({"pin": "1234", "type": "hotp"})

        assert result == "ok"
        # The pin should be hidden in the log entry message
        entry_messages = [m for m in caplog.messages if "Entering" in m]
        assert len(entry_messages) == 1
        assert "1234" not in entry_messages[0]
        assert "HIDDEN" in entry_messages[0]

    def test_hide_args_keywords_nested(self, caplog):
        logger = logging.getLogger("privacyidea.test.log_with_nested")
        logger.setLevel(logging.DEBUG)

        @log_with(logger, hide_args_keywords={0: ["password"]})
        def my_func(param):
            return "ok"

        with caplog.at_level(logging.DEBUG, logger="privacyidea.test.log_with_nested"):
            result = my_func({"user": {"password": "supersecret", "name": "admin"}})

        assert result == "ok"
        entry_messages = [m for m in caplog.messages if "Entering" in m]
        assert len(entry_messages) == 1
        assert "supersecret" not in entry_messages[0]
        assert "HIDDEN" in entry_messages[0]

    def test_hide_args_keywords_does_not_modify_original(self, caplog):
        logger = logging.getLogger("privacyidea.test.log_with_orig")
        logger.setLevel(logging.DEBUG)

        @log_with(logger, hide_args_keywords={0: ["pin"]})
        def my_func(param):
            return param

        original = {"pin": "1234", "type": "hotp"}
        with caplog.at_level(logging.DEBUG, logger="privacyidea.test.log_with_orig"):
            result = my_func(original)

        # The original dict passed to the function should not be modified
        assert result["pin"] == "1234"
        assert original["pin"] == "1234"
