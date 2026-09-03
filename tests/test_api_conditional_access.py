# (c) NetKnights GmbH 2026,  https://netknights.it
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
# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
End-to-end tests for the conditional-access engine at the
``/validate/check`` view: the pre-check that rejects an already-locked user
before any token logic runs, and the full loop where repeated failures trip a
policy stage and lock the user.
"""
from unittest import mock
from datetime import datetime, timedelta

from privacyidea.api.lib.utils import GENERIC_AUTH_FAILURE
from privacyidea.lib.error import Error
from privacyidea.lib.conditional_access.conditions import ConditionOperator, ConditionType
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType, CountMode
from privacyidea.lib.conditional_access.authentication_log import AuthLogUserRole, get_authentication_logs
from privacyidea.lib.conditional_access.engine import is_user_locked, is_ip_blocked
from privacyidea.lib.conditional_access.engine import get_user_lock, get_ip_block
from privacyidea.lib.conditional_access.engine import ConditionalAccessAction, ConditionalAccessTarget
from privacyidea.lib.conditional_access.engine import _upsert_user_lock_state
from privacyidea.lib.conditional_access.policy import create_conditional_access_policy, default_error_message
from privacyidea.lib.conditional_access.outcome_log import get_outcomes
from privacyidea.lib.conditional_access.session import get_ca_session
from privacyidea.lib.fido2.policy_action import FIDO2PolicyAction
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import SCOPE, AUTHORIZED, set_policy, delete_policy
from privacyidea.lib.smtpserver import add_smtpserver, delete_smtpserver
from privacyidea.lib.challenge import get_challenges, delete_challenges
from privacyidea.lib.token import init_token, remove_token, get_tokens, revoke_token
from privacyidea.lib.user import User
from privacyidea.lib.utils import AUTH_RESPONSE
from privacyidea.models import db, Challenge, ConditionalAccessOutcome
from privacyidea.models.authentication_log import AuthenticationLog
from privacyidea.models.conditional_access_policy import (
    BlockList,
    ConditionalAccessPolicy,
    ConditionalAccessPolicyCondition,
    ConditionalAccessPolicyCounterType,
    ConditionalAccessPolicyStage,
    ConditionalAccessStageAction,
    UserLockState,
)
from privacyidea.models.utils import utc_now
from . import smtpmock
from .authlog_utils import assert_authentication_log, assert_authentication_log_entry
from .base import MyApiTestCase


def _rows_since(before: int) -> list[str]:
    """
    The event types of the authentication-log rows written since there were *before* of them, in order.

    A conditional-access rejection classifies the request it turned away (USER_LOCKED / IP_BLOCKED / ACCESS_DENIED),
    which is what these tests assert on: the row is the only place an admin can filter for the reason, since the
    request is refused before anything else logs an outcome for it.

    Used where a test's earlier phases make the *whole* log tedious to restate; where the full log is short and
    knowable, :func:`~tests.authlog_utils.assert_authentication_log` is the better tool - it pins the complete ordered
    list plus attempt_id chaining, and pairs with
    :func:`~tests.authlog_utils.assert_authentication_log_entry`, which asserts every column of a row (so the columns
    a rejection must *not* carry are proven empty).
    """
    return [entry.event_type for entry in get_authentication_logs()[before:]]


#: The source IP the block tests use - not loopback, which is on the never-block list.
BLOCKED_IP = "203.0.113.9"


def _counter_types(counter_type):
    """Normalize a single AuthEventType (or string) or an iterable of them into
    the list-of-strings shape stored in ``ConditionalAccessPolicy.counter_types_to_track``."""
    values = counter_type if isinstance(counter_type, (list, tuple)) else [counter_type]
    return [str(t) for t in values]


def _seed_ip_spray(user: "User", event_type: AuthEventType, source_ip: str, n_users: int,
                   timestamp: datetime | None = None):
    """Seed *n_users* distinct users failing from *source_ip* (the spraying shape a
    source_ip BLOCK_IP policy keys on: one IP hitting many accounts). The users are
    synthetic (uid/username ``spray0``..) in *user*'s resolver/realm - only the distinct
    ``(username, realm, resolver)`` count matters, they need not resolve; the distinct
    ``username`` per user mirrors the resolved row a real request writes."""
    timestamp = timestamp if timestamp is not None else utc_now()
    for i in range(n_users):
        db.session.add(AuthenticationLog(
            event_type=str(event_type), resolver=user.resolver, uid=f"spray{i}",
            realm=user.realm, username=f"spray{i}", source_ip=source_ip, timestamp=timestamp))
    db.session.commit()


class ConditionalAccessValidateTestCase(MyApiTestCase):
    serial = "CA_HOTP"

    def setUp(self) -> None:
        super().setUp()
        self.setUp_user_realms()
        init_token({"serial": self.serial, "type": "hotp", "otpkey": self.otpkey, "pin": "pin"},
                   user=User("cornelius", self.realm1))
        self.user = User("cornelius", self.realm1)
        self._clear()

    def tearDown(self) -> None:
        if get_tokens(serial=self.serial):
            remove_token(self.serial)
        self._clear()
        super().tearDown()

    @staticmethod
    def _clear() -> None:
        for model in (ConditionalAccessOutcome, UserLockState, BlockList, ConditionalAccessStageAction,
                      ConditionalAccessPolicyStage, ConditionalAccessPolicyCondition,
                      ConditionalAccessPolicyCounterType, ConditionalAccessPolicy,
                      AuthenticationLog, Challenge):
            db.session.query(model).delete()
        db.session.commit()

    def _check(self, data: dict, remote_addr: str | None = None) -> dict:
        kwargs = {"environ_base": {"REMOTE_ADDR": remote_addr}} if remote_addr else {}
        with self.app.test_request_context('/validate/check', method='POST', data=data, **kwargs):
            response = self.app.full_dispatch_request()
            self.assertEqual(200, response.status_code, response)
            return response.json

    def _lock_user(self, lock_expires_at, error_message: str | None = None, user: User | None = None) -> None:
        _upsert_user_lock_state(user or self.user, lock_expires_at=lock_expires_at,
                                   error_message=error_message)

    @staticmethod
    def _make_lock_policy(*, counter_type, threshold: int, duration: int, window: int = 3600,
                          dry_run: bool = False, priority: int = 1, error_message: str | None = None) -> None:
        create_conditional_access_policy(
            name="ca_lock", time_window_seconds=window,
            counter_types_to_track=_counter_types(counter_type),
            stages=[{"failure_threshold": threshold, "error_message": error_message,
                     "actions": [{"action_type": str(ConditionalAccessAction.LOCK_USER), "action_value": duration}]}],
            target=ConditionalAccessTarget.USER, dry_run=dry_run, priority=priority)

    @staticmethod
    def _make_block_ip_policy(*, counter_type, threshold: int, duration: int, window: int = 3600,
                              priority: int = 1) -> None:
        create_conditional_access_policy(
            name="ca_blockip", time_window_seconds=window,
            counter_types_to_track=_counter_types(counter_type),
            stages=[{"failure_threshold": threshold,
                     "actions": [{"action_type": str(ConditionalAccessAction.BLOCK_IP), "action_value": duration}]}],
            target=ConditionalAccessTarget.SOURCE_IP, priority=priority)

    @staticmethod
    def _make_decision_policy(*, name: str, counter_type, threshold: int, action,
                              priority: int = 1, window: int = 3600) -> None:
        create_conditional_access_policy(
            name=name, time_window_seconds=window,
            counter_types_to_track=_counter_types(counter_type),
            stages=[{"failure_threshold": threshold,
                     "actions": [{"action_type": str(action), "action_value": None}]}],
            target=ConditionalAccessTarget.USER, priority=priority)

    def _failcount(self) -> int:
        return get_tokens(serial=self.serial)[0].token.failcount

    # --- pre-check ------------------------------------------------------------

    def test_locked_user_rejected_without_token_logic(self):
        # Confirm the credentials are valid before locking, so the rejection below is provably the conditional-access
        # lock and not a bad OTP.
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)

        # mock a user lock
        self._lock_user(utc_now() + timedelta(seconds=600))
        self.assertEqual(0, self._failcount())

        # The very same request is now rejected while the user is locked.
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["status"], body)
        self.assertFalse(body["result"]["value"], body)
        # Generic response: the detail says what any failed authentication says and nothing more. This is the
        # shape a rejection has, and the one a stage tripped mid-request has to match (see
        # test_a_challenge_that_trips_a_lock_is_refused_like_any_other_request).
        self.assertSetEqual({"message", "threadid"}, set(body["detail"]), body)
        self.assertEqual(str(GENERIC_AUTH_FAILURE), body["detail"]["message"], body)
        # No token logic ran: the fail counter did not move and no valid OTP was consumed.
        self.assertEqual(0, self._failcount())
        # The rejection is what classifies this request: no token logic ran, so nothing else would log an outcome.
        entries = assert_authentication_log([AuthEventType.LOGIN_SUCCESS, AuthEventType.USER_LOCKED],
                                            same_attempt=False)
        # Every other column is asserted empty - no serial, no client label, no other_info - since a rejection row
        # carries nothing else and the lock's own outcome already records the expiry.
        assert_authentication_log_entry(entries[AuthEventType.USER_LOCKED], user=self.user)

    def test_configured_message_is_surfaced_on_validate_check(self):
        # The machine-facing endpoint carries the error message in detail.message - a different shape from
        # /auth's result.error.message, which is why it needs its own coverage.
        self._lock_user(utc_now() + timedelta(seconds=600), error_message="Locked. Try again in about {duration}.")
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertFalse(body["result"]["value"], body)
        # {duration} is rendered against the time left now, not stored pre-rendered.
        self.assertEqual("Locked. Try again in about 10 minute(s).", body["detail"]["message"], body)

    def test_no_configured_message_leaves_the_ordinary_failure(self):
        # The default: nothing of conditional access's, just the failure any other rejection returns. Not an
        # empty detail - that would be a tell in itself, since every other failure carries one.
        self._lock_user(utc_now() + timedelta(seconds=600))
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertFalse(body["result"]["value"], body)
        self.assertEqual(str(GENERIC_AUTH_FAILURE), body["detail"]["message"], body)

    def test_the_request_that_trips_the_lock_reports_it(self):
        # The lock is written during this very request - and any EMAIL_* action is sent now, not on the
        # next login - so this is the response that reports it, not merely the ones after it.
        self._make_lock_policy(counter_type=AuthEventType.PIN_FAIL, threshold=2, duration=600,
                               error_message="Locked. Try again in about {duration}.")
        first = self._check({"user": "cornelius", "pass": "wrongpin123456"})
        self.assertFalse(first["result"]["value"], first)
        # Below the threshold nothing has happened yet, so the ordinary token failure stands.
        self.assertEqual("wrong otp pin", first["detail"]["message"], first)

        tripping = self._check({"user": "cornelius", "pass": "wrongpin123456"})
        self.assertFalse(tripping["result"]["value"], tripping)
        self.assertEqual("Locked. Try again in about 10 minute(s).", tripping["detail"]["message"], tripping)
        self.assertTrue(is_user_locked(self.user))

    def test_the_request_that_trips_a_lock_on_triggerchallenge_reports_it(self):
        # /validate/triggerchallenge has the gate, so it must also report a stage it trips - otherwise the
        # admin driving it is answered with the plain result while the *next* request carries the message.
        # A user with no challenge-capable token logs NO_TOKEN, which a policy may count like any failure.
        self._make_lock_policy(counter_type=AuthEventType.NO_TOKEN, threshold=1, duration=600,
                               error_message="Locked. Try again in about {duration}.")
        with self.app.test_request_context("/validate/triggerchallenge", method="POST",
                                           data={"user": "selfservice", "realm": self.realm1},
                                           headers={"PI-Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res.json)
            body = res.json
        # No token to challenge, so nothing was triggered - and the lock this very request wrote is what the
        # response leads with rather than the bare count.
        self.assertEqual(0, body["result"]["value"], body)
        self.assertSetEqual({"message", "threadid"}, set(body["detail"]), body)
        self.assertEqual("Locked. Try again in about 10 minute(s).", body["detail"]["message"], body)
        self.assertTrue(is_user_locked(User("selfservice", self.realm1)))

    def test_a_challenge_that_succeeds_and_trips_a_lock_is_still_withdrawn(self):
        # What decides is the restriction, not whether the response looked like a failure. That distinction matters
        # here because result.value is the *number of challenges triggered*, so a request that both triggers one and
        # trips a lock reads as a success - yet handing the client a transaction_id the pre-check would refuse on the
        # very next request would answer differently from every request the lock then refuses.
        self._make_lock_policy(counter_type=AuthEventType.CHALLENGE_TRIGGERED, threshold=1, duration=600,
                               error_message="Locked. Try again in about {duration}.")
        with self.app.test_request_context("/validate/triggerchallenge", method="POST",
                                           data={"user": "cornelius", "realm": self.realm1},
                                           headers={"PI-Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res.json)
            body = res.json
        self.assertTrue(is_user_locked(self.user))
        # 0, not False: the value is a count on this endpoint, so a rejection answers with its kind of nothing.
        self.assertEqual(0, body["result"]["value"], body)
        self.assertNotIsInstance(body["result"]["value"], bool, body)
        self.assertEqual(AUTH_RESPONSE.REJECT, body["result"]["authentication"], body)
        # The reason and nothing that describes the challenge it overtook.
        self.assertSetEqual({"message", "threadid"}, set(body["detail"]), body)
        self.assertEqual("Locked. Try again in about 10 minute(s).", body["detail"]["message"], body)
        # Withdrawn, not invalidated: the row is left to expire unanswered, exactly as on /validate/check.
        self.assertTrue(get_challenges(serial=self.serial))

    def test_triggering_a_challenge_without_a_restriction_is_untouched(self):
        # The other half of the count-as-value shape, and what the rewritten test above must not cost: with a
        # policy in place but nothing tripped, a triggered challenge is reported exactly as it would be with no
        # policy at all - a truthy count still reads as "worked".
        self._make_lock_policy(counter_type=AuthEventType.CHALLENGE_TRIGGERED, threshold=99, duration=600,
                               error_message="Should not be shown.")
        with self.app.test_request_context("/validate/triggerchallenge", method="POST",
                                           data={"user": "cornelius", "realm": self.realm1},
                                           headers={"PI-Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res.json)
            body = res.json
        self.assertFalse(is_user_locked(self.user))
        self.assertEqual(1, body["result"]["value"], body)
        self.assertNotIn("Should not be shown.", str(body["detail"]), body)
        self.assertTrue(body["detail"]["transaction_ids"], body)
        self.assertEqual([self.serial], [entry["serial"] for entry in body["detail"]["multi_challenge"]], body)

    def test_a_challenge_that_trips_a_lock_is_refused_like_any_other_request(self):
        # A stage can be tripped by a challenge trigger like by any other tracked event. When it restricts, this
        # request is refused - so the response carries the reason and nothing else, the challenge it was about to
        # hand out included.
        set_policy(name="ca_chalresp", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.CHALLENGERESPONSE}=hotp")
        self._make_lock_policy(counter_type=AuthEventType.CHALLENGE_TRIGGERED, threshold=1, duration=600,
                               error_message="Locked. Try again in about {duration}.")
        try:
            body = self._check({"user": "cornelius", "pass": "pin"})
        finally:
            delete_policy("ca_chalresp")
        self.assertFalse(body["result"]["value"], body)
        self.assertTrue(is_user_locked(self.user))
        # One rule for what a conditional-access rejection says, whatever the request was doing when it was
        # refused: the reason, and nothing that describes what it overtook.
        # The whole detail, not just the absence of the keys this test thought to name: everything else in it
        # described the challenge, and none of it may survive a rejection. threadid identifies the request
        # rather than saying anything about it, so it stays.
        self.assertSetEqual({"message", "threadid"}, set(body["detail"]), body)
        self.assertEqual("Locked. Try again in about 10 minute(s).", body["detail"]["message"], body)
        # REJECT rather than CHALLENGE: the challenge was withdrawn, so this response is a refusal like any other.
        self.assertEqual(AUTH_RESPONSE.REJECT, body["result"]["authentication"], body)
        # Writing the lock does not reclassify the request: USER_LOCKED is what the *pre-check* of a later
        # request logs, so this one is still filed as the challenge trigger it was.
        self.assertListEqual([AuthEventType.CHALLENGE_TRIGGERED],
                             [entry.event_type for entry in get_authentication_logs()])

    def test_the_challenge_row_is_left_alone_by_the_rejection(self):
        # Withdrawing the challenge from the response is not invalidating it: conditional access does not reach
        # into the challenge itself, it simply never tells the client about it, and the row expires unanswered.
        set_policy(name="ca_chalresp", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.CHALLENGERESPONSE}=hotp")
        self._make_lock_policy(counter_type=AuthEventType.CHALLENGE_TRIGGERED, threshold=1, duration=600,
                               error_message="Locked.")
        try:
            self._check({"user": "cornelius", "pass": "pin"})
        finally:
            delete_policy("ca_chalresp")
        # get_challenges(serial=...), not a count on the Challenge table: with PI_REDIS_CACHE_CHALLENGES the
        # challenge lives in Redis and the table is empty, so a table count would "prove" the row was deleted on
        # every run. Keyed by serial because the cache cannot enumerate.
        self.assertEqual(1, len(get_challenges(serial=self.serial)))

    def test_a_notification_is_appended_to_a_challenge_it_was_tripped_by(self):
        # The other shape: a notify-only stage adds to what the response already said instead of replacing it,
        # on a challenge exactly as on a failure. Threshold 2, so the first call is an untripped challenge to
        # measure the second against - the detail must differ in nothing but the message.
        set_policy(name="ca_chalresp", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.CHALLENGERESPONSE}=hotp")
        add_smtpserver(identifier="ca_notify_mail", server="1.2.3.4", tls=False)
        create_conditional_access_policy(
            name="notify_on_challenge", time_window_seconds=3600,
            counter_types_to_track=_counter_types(AuthEventType.CHALLENGE_TRIGGERED),
            stages=[{"failure_threshold": 2, "error_message": "Your administrator was notified.",
                     "actions": [{"action_type": str(ConditionalAccessAction.EMAIL_ADMIN),
                                  "action_value": {"smtp_identifier": "ca_notify_mail",
                                                   "recipient_group": "soc@example.com",
                                                   "subject": "s", "body": "b"}}]}],
            target=ConditionalAccessTarget.USER, priority=1)
        try:
            with mock.patch("privacyidea.lib.conditional_access.engine._send_action_email", return_value=True):
                untripped = self._check({"user": "cornelius", "pass": "pin"})
                body = self._check({"user": "cornelius", "pass": "pin"})
        finally:
            delete_policy("ca_chalresp")
            delete_smtpserver("ca_notify_mail")
        self.assertNotIn("Your administrator was notified.", untripped["detail"]["message"], untripped)
        # Appended to the challenge's own prompt, not in place of it.
        self.assertEqual(f"{untripped['detail']['message'].rstrip('.')}. Your administrator was notified.",
                         body["detail"]["message"], body)
        # And nothing else moved: the same keys an untripped challenge carries, and a usable challenge in them.
        self.assertSetEqual(set(untripped["detail"]), set(body["detail"]), body)
        self.assertTrue(body["detail"]["transaction_id"], body)
        self.assertEqual(self.serial, body["detail"]["serial"], body)
        self.assertFalse(is_user_locked(self.user))

    def test_a_challenge_from_before_the_lock_is_refused_when_it_is_answered(self):
        # A challenge handed out below the threshold stays answerable, and the answer is what meets the lock:
        # the pre-check refuses it with the same wording, so nothing is lost by not repeating it earlier.
        set_policy(name="ca_chalresp", scope=SCOPE.AUTH,
                   action=f"{PolicyAction.CHALLENGERESPONSE}=hotp")
        self._make_lock_policy(counter_type=AuthEventType.CHALLENGE_TRIGGERED, threshold=2, duration=600,
                               error_message="Locked. Try again in about {duration}.")
        try:
            # Below the threshold: an ordinary challenge, untouched.
            triggered = self._check({"user": "cornelius", "pass": "pin"})
            transaction_id = triggered["detail"]["transaction_id"]
            self.assertEqual(AUTH_RESPONSE.CHALLENGE, triggered["result"]["authentication"], triggered)
            self.assertFalse(is_user_locked(self.user))
            # A second trigger reaches it and writes the lock.
            self._check({"user": "cornelius", "pass": "pin"})
            self.assertTrue(is_user_locked(self.user))
            answered = self._check({"user": "cornelius", "pass": "755224", "transaction_id": transaction_id})
        finally:
            delete_policy("ca_chalresp")
        self.assertFalse(answered["result"]["value"], answered)
        self.assertEqual("Locked. Try again in about 10 minute(s).", answered["detail"]["message"], answered)

    def test_the_tripping_request_says_only_what_a_rejection_says(self):
        # With no wording configured the rejection says what every other failed authentication says - not what the
        # token said about the credential it overtook. See
        # test_a_silent_restriction_answers_like_the_rejections_after_it for the whole-response comparison.
        self._make_lock_policy(counter_type=AuthEventType.PIN_FAIL, threshold=2, duration=600)
        self._check({"user": "cornelius", "pass": "wrongpin123456"})
        tripping = self._check({"user": "cornelius", "pass": "wrongpin123456"})
        self.assertEqual(str(GENERIC_AUTH_FAILURE), tripping["detail"]["message"], tripping)
        self.assertTrue(is_user_locked(self.user))

    def test_both_restrictions_are_reported_on_validate_check(self):
        # Both restrictions are reported, most severe first: a user facing a permanent block behind a timed
        # lock must not be told only to "try again in 10 minutes" when waiting cannot help.
        self._lock_user(utc_now() + timedelta(seconds=600), error_message="LOCK-TEXT")
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=None, error_message="PERMANENT-BLOCK-TEXT"))
        db.session.commit()
        body = self._check({"user": "cornelius", "pass": "pin755224"}, remote_addr="203.0.113.7")
        self.assertFalse(body["result"]["value"], body)
        # The permanent block leads; the timed lock follows.
        self.assertEqual("PERMANENT-BLOCK-TEXT LOCK-TEXT", body["detail"]["message"], body)

    def test_the_other_restriction_is_recorded_on_the_row(self):
        # The log records one event_type per request, so a request refused by both is filed under the binding
        # one and the other is listed in other_info as additional_event_types: not queryable the way
        # event_type is, but visible to an admin reading the entry.
        self._lock_user(utc_now() + timedelta(seconds=600))
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=None))
        db.session.commit()
        self._check({"user": "cornelius", "pass": "pin755224"}, remote_addr="203.0.113.7")
        entries = get_authentication_logs()
        self.assertEqual(1, len(entries), entries)
        # The permanent block binds, so that is the classification; the lock is the one recorded alongside.
        self.assertEqual(str(AuthEventType.IP_BLOCKED), entries[0].event_type, entries[0])
        self.assertListEqual([str(AuthEventType.USER_LOCKED)], entries[0].other_info["additional_event_types"],
                             entries[0])

    def test_a_single_restriction_records_nothing_extra(self):
        # Only one in force, so the event type says it all and the row carries no redundant note.
        self._lock_user(utc_now() + timedelta(seconds=600))
        self._check({"user": "cornelius", "pass": "pin755224"})
        entries = get_authentication_logs()
        self.assertEqual(str(AuthEventType.USER_LOCKED), entries[0].event_type, entries[0])
        self.assertNotIn("additional_event_types", entries[0].other_info or {}, entries[0])

    def test_a_restriction_written_by_a_raising_request_is_still_answered_as_a_rejection(self):
        # A view that raises skips every post-policy, so the response is built by an error handler. The engine
        # still runs (at teardown), so the lock is written either way - and the response has to say so, as a
        # rejection: the endpoint's own error must not survive, because "the token is locked" states the very
        # reason a rejection withholds.
        remove_token(self.serial)
        init_token({"serial": self.serial, "type": "hotp", "otpkey": self.otpkey, "pin": "pin"}, user=self.user)
        revoke_token(self.serial)
        self._make_lock_policy(counter_type=AuthEventType.NO_USABLE_TOKEN, threshold=1, duration=600,
                               error_message="Locked. Try again in about {duration}.")

        tripping = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(is_user_locked(self.user))
        # The rejection shape, not the error shape: no result.error, and nothing of ERR1007 anywhere.
        self.assertNotIn("error", tripping["result"], tripping)
        self.assertTrue(tripping["result"]["status"], tripping)
        self.assertFalse(tripping["result"]["value"], tripping)
        self.assertEqual(AUTH_RESPONSE.REJECT, tripping["result"]["authentication"], tripping)
        self.assertSetEqual({"message", "threadid"}, set(tripping["detail"]), tripping)
        self.assertEqual("Locked. Try again in about 10 minute(s).", tripping["detail"]["message"], tripping)
        self.assertNotIn("locked", str(tripping).replace("Locked.", ""), tripping)

        # And it is the same answer the pre-check gives the requests after it.
        after = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertEqual(after["result"], tripping["result"], tripping)
        self.assertEqual(after["detail"], tripping["detail"], tripping)

    def test_a_raising_request_without_a_restriction_keeps_its_own_error(self):
        # The counterpart: conditional access only overtakes a response it actually refused. With nothing
        # restricted the endpoint's error stands exactly as it did, code and all.
        remove_token(self.serial)
        init_token({"serial": self.serial, "type": "hotp", "otpkey": self.otpkey, "pin": "pin"}, user=self.user)
        revoke_token(self.serial)
        with self.app.test_request_context("/validate/check", method="POST",
                                           data={"user": "cornelius", "pass": "pin755224"}):
            res = self.app.full_dispatch_request()
        self.assertEqual(400, res.status_code, res.json)
        self.assertEqual(Error.TOKEN_LOCKED, res.json["result"]["error"]["code"], res.json)

    def test_a_silent_restriction_on_a_raising_request_answers_generically(self):
        # Silent stays silent here too: the rejection says what every other failed authentication says, which is
        # again exactly what the pre-check answers the following requests with.
        remove_token(self.serial)
        init_token({"serial": self.serial, "type": "hotp", "otpkey": self.otpkey, "pin": "pin"}, user=self.user)
        revoke_token(self.serial)
        self._make_lock_policy(counter_type=AuthEventType.NO_USABLE_TOKEN, threshold=1, duration=600)

        tripping = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(is_user_locked(self.user))
        self.assertEqual(str(GENERIC_AUTH_FAILURE), tripping["detail"]["message"], tripping)
        after = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertEqual(after["detail"], tripping["detail"], tripping)

    def test_hide_specific_error_message_leaves_the_message_alone_on_validate_check(self):
        # The /validate mirror: the postpolicy replaces the whole detail, but not this error message.
        from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
        from privacyidea.lib.policies.actions import PolicyAction
        self._lock_user(utc_now() + timedelta(seconds=600), error_message="Locked. Try again later.")
        set_policy(name="ca_hide", scope=SCOPE.AUTH, action=f"{PolicyAction.HIDE_SPECIFIC_ERROR_MESSAGE}")
        try:
            body = self._check({"user": "cornelius", "pass": "pin755224"})
            self.assertFalse(body["result"]["value"], body)
            self.assertEqual("Locked. Try again later.", body["detail"]["message"], body)
        finally:
            delete_policy("ca_hide")

    def test_a_silent_restriction_answers_like_the_rejections_after_it(self):
        # The request that writes a lock is answered exactly as the requests the lock then refuses: the whole
        # response, not merely the wording, and whether or not a stage carried any. So the token's own "wrong otp
        # pin" and its details give way to the ordinary failure, because that is what the pre-check returns.
        #
        # The cost is accepted deliberately: a silent lock *is* detectable at the moment it trips, since the
        # response changes shape. The alternative was worse - one lock answering two different ways depending on
        # which request you happened to catch it on.
        self._make_lock_policy(counter_type=AuthEventType.PIN_FAIL, threshold=2, duration=600)
        below = self._check({"user": "cornelius", "pass": "wrongpin123456"})
        self.assertEqual("wrong otp pin", below["detail"]["message"], below)

        tripping = self._check({"user": "cornelius", "pass": "wrongpin123456"})
        self.assertTrue(is_user_locked(self.user))
        # The correct password, refused by the pre-check - so any difference here is the two paths disagreeing.
        after = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertEqual(after["result"], tripping["result"], tripping)
        self.assertEqual(after["detail"], tripping["detail"], tripping)
        self.assertEqual(str(GENERIC_AUTH_FAILURE), tripping["detail"]["message"], tripping)

    def test_hide_specific_error_message_still_masks_an_ordinary_token_failure(self):
        # The policy keeps doing its job on everything that is not conditional access's: a wrong PIN is still
        # generic, so keeping the lock error message does not widen what else the endpoint discloses.
        from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
        from privacyidea.lib.policies.actions import PolicyAction
        set_policy(name="ca_hide", scope=SCOPE.AUTH, action=f"{PolicyAction.HIDE_SPECIFIC_ERROR_MESSAGE}")
        try:
            body = self._check({"user": "cornelius", "pass": "wrongpin123456"})
            self.assertFalse(body["result"]["value"], body)
            self.assertEqual("Authentication failed.", body["detail"]["message"], body)
        finally:
            delete_policy("ca_hide")

    def test_no_detail_on_fail_keeps_the_configured_message(self):
        # Same rule as hide_specific_error_message: the action strips what privacyIDEA volunteers about the attempt,
        # not wording an admin opted into. Without this the pre-check answered with no detail at all while the
        # request that *wrote* the lock answered with the message - one lock, worded two ways.
        from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
        from privacyidea.lib.policies.actions import PolicyAction
        self._lock_user(utc_now() + timedelta(seconds=600), error_message="Locked. Try again in about {duration}.")
        set_policy(name="ca_nodetail", scope=SCOPE.AUTHZ, action=f"{PolicyAction.NODETAILFAIL}")
        try:
            body = self._check({"user": "cornelius", "pass": "pin755224"})
            self.assertFalse(body["result"]["value"], body)
            # The message and nothing else: the rejection has nothing else to put there anyway.
            self.assertSetEqual({"message"}, set(body["detail"]), body)
            self.assertEqual("Locked. Try again in about 10 minute(s).", body["detail"]["message"], body)
        finally:
            delete_policy("ca_nodetail")

    def test_no_detail_on_fail_still_strips_an_ordinary_failure(self):
        # The action keeps doing its job on everything that is not conditional access's, and on a silent lock:
        # keeping a configured message does not widen what else the endpoint discloses.
        from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
        from privacyidea.lib.policies.actions import PolicyAction
        set_policy(name="ca_nodetail", scope=SCOPE.AUTHZ, action=f"{PolicyAction.NODETAILFAIL}")
        try:
            ordinary = self._check({"user": "cornelius", "pass": "wrongpin123456"})
            self.assertFalse(ordinary["result"]["value"], ordinary)
            self.assertNotIn("detail", ordinary, ordinary)

            # A lock carrying no error message is not conditional access's to keep either, so it strips like any
            # other failure - which is what keeps a silent lock indistinguishable from a wrong PIN.
            self._lock_user(utc_now() + timedelta(seconds=600))
            silent = self._check({"user": "cornelius", "pass": "pin755224"})
            self.assertNotIn("detail", silent, silent)
        finally:
            delete_policy("ca_nodetail")

    def test_the_request_that_trips_the_lock_reports_it_under_no_detail_on_fail(self):
        # The other half of the pair above: the pre-check and the request that writes the lock must answer with the
        # same wording, whichever of them the policy stack happens to reach.
        from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
        from privacyidea.lib.policies.actions import PolicyAction
        self._make_lock_policy(counter_type=AuthEventType.PIN_FAIL, threshold=1, duration=600,
                               error_message="Locked. Try again in about {duration}.")
        set_policy(name="ca_nodetail", scope=SCOPE.AUTHZ, action=f"{PolicyAction.NODETAILFAIL}")
        try:
            tripping = self._check({"user": "cornelius", "pass": "wrongpin123456"})
            self.assertTrue(is_user_locked(self.user))
            self.assertEqual("Locked. Try again in about 10 minute(s).", tripping["detail"]["message"], tripping)
            # And the next request, refused by the pre-check, says exactly the same thing.
            after = self._check({"user": "cornelius", "pass": "pin755224"})
            self.assertEqual(tripping["detail"]["message"], after["detail"]["message"], after)
        finally:
            delete_policy("ca_nodetail")

    @smtpmock.activate
    def test_no_detail_on_fail_masks_the_reason_a_notification_was_appended_to(self):
        # A notification is appended to the failure's own reason, and that reason is exactly what this action
        # strips. Only the stage's own sentence may come through.
        from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
        from privacyidea.lib.policies.actions import PolicyAction
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        set_policy(name="ca_nodetail", scope=SCOPE.AUTHZ, action=f"{PolicyAction.NODETAILFAIL}")
        try:
            create_conditional_access_policy(
                name="ca_mail", time_window_seconds=3600,
                counter_types_to_track=_counter_types(AuthEventType.PIN_FAIL),
                stages=[{"failure_threshold": 1, "error_message": "Your administrator has been notified.",
                         "actions": [{"action_type": str(ConditionalAccessAction.EMAIL_ADMIN),
                                      "action_value": {"smtp_identifier": "lockoutmail",
                                                       "recipient_group": "soc@example.com",
                                                       "subject": "s", "body": "b"}}]}],
                target=ConditionalAccessTarget.USER, priority=1)

            body = self._check({"user": "cornelius", "pass": "wrongpin123456"})
            self.assertNotIn("wrong otp pin", body["detail"]["message"], body)
            self.assertIn("Your administrator has been notified.", body["detail"]["message"], body)
        finally:
            delete_policy("ca_nodetail")
            delete_smtpserver("lockoutmail")

    @smtpmock.activate
    def test_hide_specific_error_message_masks_the_reason_a_notification_was_appended_to(self):
        # A notify-only stage is *appended* to the failure's own reason, so the response reads "wrong otp pin. Your
        # administrator has been notified." Only the second half is conditional access's to keep: keeping the whole
        # sentence would carry the token-layer reason straight past the policy that exists to suppress it.
        from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
        from privacyidea.lib.policies.actions import PolicyAction
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        set_policy(name="ca_hide", scope=SCOPE.AUTH, action=f"{PolicyAction.HIDE_SPECIFIC_ERROR_MESSAGE}")
        try:
            create_conditional_access_policy(
                name="ca_mail", time_window_seconds=3600,
                counter_types_to_track=_counter_types(AuthEventType.PIN_FAIL),
                stages=[{"failure_threshold": 1, "error_message": "Your administrator has been notified.",
                         "actions": [{"action_type": str(ConditionalAccessAction.EMAIL_ADMIN),
                                      "action_value": {"smtp_identifier": "lockoutmail",
                                                       "recipient_group": "soc@example.com",
                                                       "subject": "s", "body": "b"}}]}],
                target=ConditionalAccessTarget.USER, priority=1)

            body = self._check({"user": "cornelius", "pass": "wrongpin123456"})
            self.assertFalse(body["result"]["value"], body)
            # The stage's own sentence survives; the reason it was appended to does not.
            self.assertEqual(f"{str(GENERIC_AUTH_FAILURE).rstrip('.')}. Your administrator has been notified.",
                             body["detail"]["message"], body)
            self.assertNotIn("wrong otp pin", body["detail"]["message"], body)
            self.assertListEqual(["soc@example.com"], smtpmock.get_sent_recipient())
        finally:
            delete_policy("ca_hide")
            delete_smtpserver("lockoutmail")

    @smtpmock.activate
    def test_a_notification_keeps_the_failure_reason_when_nothing_masks_it(self):
        # The counterpart: with no masking policy the credential failure is still why the request was refused, so
        # the notification is appended to it rather than replacing it.
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        try:
            create_conditional_access_policy(
                name="ca_mail", time_window_seconds=3600,
                counter_types_to_track=_counter_types(AuthEventType.PIN_FAIL),
                stages=[{"failure_threshold": 1, "error_message": "Your administrator has been notified.",
                         "actions": [{"action_type": str(ConditionalAccessAction.EMAIL_ADMIN),
                                      "action_value": {"smtp_identifier": "lockoutmail",
                                                       "recipient_group": "soc@example.com",
                                                       "subject": "s", "body": "b"}}]}],
                target=ConditionalAccessTarget.USER, priority=1)

            body = self._check({"user": "cornelius", "pass": "wrongpin123456"})
            self.assertEqual("wrong otp pin. Your administrator has been notified.",
                             body["detail"]["message"], body)
        finally:
            delete_smtpserver("lockoutmail")

    def test_the_policy_supplies_an_error_message_a_stage_did_not(self):
        # The simplified form of writing the suggestion onto every stage: with the policy on, a lock that
        # carries no error message of its own is still described - by the standard error message for what it is.
        from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
        from privacyidea.lib.policies.actions import PolicyAction
        self._lock_user(utc_now() + timedelta(seconds=600))
        without = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertEqual(str(GENERIC_AUTH_FAILURE), without["detail"]["message"], without)

        set_policy(name="ca_show", scope=SCOPE.CONDITIONAL_ACCESS,
                   action=f"{PolicyAction.SHOW_DEFAULT_CA_ERROR_MESSAGE}")
        try:
            body = self._check({"user": "cornelius", "pass": "pin755224"})
            self.assertEqual(str(default_error_message(ConditionalAccessAction.LOCK_USER)).replace(
                "{duration}", "10 minute(s)"), body["detail"]["message"], body)
        finally:
            delete_policy("ca_show")

    def test_a_stage_of_its_own_still_wins_over_the_policy(self):
        # The policy never overrides an error message an admin wrote: it only stands in where none was.
        from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
        from privacyidea.lib.policies.actions import PolicyAction
        self._lock_user(utc_now() + timedelta(seconds=600), error_message="MSG-OWN")
        set_policy(name="ca_show", scope=SCOPE.CONDITIONAL_ACCESS,
                   action=f"{PolicyAction.SHOW_DEFAULT_CA_ERROR_MESSAGE}")
        try:
            body = self._check({"user": "cornelius", "pass": "pin755224"})
            self.assertEqual("MSG-OWN", body["detail"]["message"], body)
        finally:
            delete_policy("ca_show")

    def test_the_policy_describes_the_request_that_trips_the_lock(self):
        # The post-response evaluation answers the same way the pre-check does - the gate resolves the policy
        # once and the request context carries it, so one request cannot word a rejection two ways.
        from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
        from privacyidea.lib.policies.actions import PolicyAction
        self._make_lock_policy(counter_type=AuthEventType.PIN_FAIL, threshold=2, duration=600)
        set_policy(name="ca_show", scope=SCOPE.CONDITIONAL_ACCESS,
                   action=f"{PolicyAction.SHOW_DEFAULT_CA_ERROR_MESSAGE}")
        try:
            self._check({"user": "cornelius", "pass": "wrongpin123456"})
            tripping = self._check({"user": "cornelius", "pass": "wrongpin123456"})
            self.assertTrue(is_user_locked(self.user))
            self.assertEqual(str(default_error_message(ConditionalAccessAction.LOCK_USER)).replace(
                "{duration}", "10 minute(s)"), tripping["detail"]["message"], tripping)
        finally:
            delete_policy("ca_show")

    def test_the_policy_describes_a_blocked_address(self):
        # The IP side of the fallback: a block is described by the standard error message for its shape, the
        # same way a lock is.
        from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
        from privacyidea.lib.policies.actions import PolicyAction
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        set_policy(name="ca_show", scope=SCOPE.CONDITIONAL_ACCESS,
                   action=f"{PolicyAction.SHOW_DEFAULT_CA_ERROR_MESSAGE}")
        try:
            body = self._check({"user": "cornelius", "pass": "pin755224"}, remote_addr="203.0.113.7")
            self.assertFalse(body["result"]["value"], body)
            self.assertEqual(str(default_error_message(ConditionalAccessAction.BLOCK_IP)).replace(
                "{duration}", "10 minute(s)"), body["detail"]["message"], body)
        finally:
            delete_policy("ca_show")

    def test_the_policy_applies_to_a_request_that_resolves_no_user(self):
        # An unassigned token authenticating by serial: nothing resolves a user, so the policy is matched with
        # an empty one. That is not a gap - Match.user passes the client IP itself, so a policy scoped to a
        # client still applies. Only conditions naming a user, realm or resolver drop out, which is right for a
        # request that belongs to none of them.
        from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
        from privacyidea.lib.policies.actions import PolicyAction
        init_token({"serial": "CA_ORPHAN", "type": "hotp", "otpkey": self.otpkey, "pin": "pin"})
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        set_policy(name="ca_show", scope=SCOPE.CONDITIONAL_ACCESS,
                   action=f"{PolicyAction.SHOW_DEFAULT_CA_ERROR_MESSAGE}")
        try:
            body = self._check({"serial": "CA_ORPHAN", "pass": "pin755224"}, remote_addr="203.0.113.7")
            self.assertFalse(body["result"]["value"], body)
            self.assertEqual(str(default_error_message(ConditionalAccessAction.BLOCK_IP)).replace(
                "{duration}", "10 minute(s)"), body["detail"]["message"], body)
            # The rejection really did belong to nobody: the row it wrote names no user to match against.
            entries = get_authentication_logs()
            self.assertEqual(str(AuthEventType.IP_BLOCKED), entries[0].event_type, entries[0])
            self.assertFalse(entries[0].username, entries[0])
            self.assertFalse(entries[0].realm, entries[0])
        finally:
            delete_policy("ca_show")
            remove_token("CA_ORPHAN")

    def test_expired_lock_does_not_reject(self):
        self._lock_user(utc_now() - timedelta(seconds=10))
        # An expired lock is not a lock: a valid authentication still succeeds.
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)
        # The stale row carries no state; the pre-check deletes it on this login rather than waiting for the bulk purge
        # command.
        self.assertIsNone(db.session.get(UserLockState, (self.user.resolver, self.user.uid, self.user.realm)))

    # --- full loop ------------------------------------------------------------

    def test_user_locked_after_threshold_failures(self):
        # 3 wrong OTPs (correct PIN) within the window -> MFA_FAIL -> 10-minute lock.
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=3, duration=600)

        for _ in range(3):
            body = self._check({"user": "cornelius", "pass": "pin000000"})
            self.assertFalse(body["result"]["value"], body)

        # The three MFA_FAIL events tripped the stage and locked the user.
        self.assertEqual(3, len(get_authentication_logs()))
        self.assertEqual([AuthEventType.MFA_FAIL] * 3,
                         [entry.event_type for entry in get_authentication_logs()])
        self.assertTrue(is_user_locked(self.user))

        # The next request is rejected by the pre-check: no further token logic, and the rejection classifies it.
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.MFA_FAIL] * 3 + [AuthEventType.USER_LOCKED],
                                            same_attempt=False)
        assert_authentication_log_entry(entries.all[-1], user=self.user)

    def test_a_lock_that_was_never_written_does_not_refuse_its_own_request(self):
        # A restricting action that did not restrict anything must not turn its own request into a rejection: the
        # response would say what a lock says while no lock exists, and the very next request would authenticate.
        # Here the duration cannot be read (action_value uses a key parse_lock_duration_seconds does not look at),
        # so the write is skipped - the same shape as a BLOCK_IP on a request with no source IP, or a write that
        # fails outright.
        #
        # Written straight through the ORM rather than create_conditional_access_policy: the CRUD layer now
        # validates action_value at write time and would reject this shape outright, so this simulates a row
        # written before that rule existed (or straight to the database) to exercise the engine's own defense.
        policy = ConditionalAccessPolicy(
            name="ca_lock_unusable", time_window_seconds=3600, priority=1,
            target=str(ConditionalAccessTarget.USER), counter_types_to_track=_counter_types(AuthEventType.PIN_FAIL))
        policy.stages = [ConditionalAccessPolicyStage(
            failure_threshold=1,
            actions=[ConditionalAccessStageAction(action_type=str(ConditionalAccessAction.LOCK_USER),
                                                  action_value={"lock_duration_seconds": 600})])]
        db.session.add(policy)
        db.session.commit()

        body = self._check({"user": "cornelius", "pass": "wrongpin"})
        # The token failure is still the reason the request failed, and still says so.
        self.assertEqual("wrong otp pin", body["detail"]["message"], body)
        self.assertEqual(AUTH_RESPONSE.REJECT, body["result"]["authentication"], body)
        self.assertFalse(is_user_locked(self.user))
        # Nothing ran, so nothing is recorded as having happened on the row this request wrote.
        entries = get_authentication_logs()
        self.assertListEqual([], list(get_outcomes(entries[-1].id)))
        # And the next request is not refused, which is the disagreement the rejection would have created.
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)

    def test_a_stage_whose_lock_was_skipped_still_says_nothing_about_it(self):
        # The other half of the same rule, and the reason "did it restrict anything" and "may it speak" are two
        # questions: the stage's one error message describes the lock it aimed at, so a stage that only managed to
        # send its mail must not append that sentence - a lock that is not in force, carrying a {duration} there is
        # nothing to substitute against - to a failure it did not cause.
        #
        # Written straight through the ORM: the CRUD layer now validates action_value at write time and would
        # reject the unusable LOCK_USER duration and the incomplete EMAIL_ADMIN value outright, so this simulates
        # rows written before that rule existed.
        policy = ConditionalAccessPolicy(
            name="ca_lock_unusable", time_window_seconds=3600, priority=1,
            target=str(ConditionalAccessTarget.USER), counter_types_to_track=_counter_types(AuthEventType.PIN_FAIL))
        policy.stages = [ConditionalAccessPolicyStage(
            failure_threshold=1, error_message="Your account is locked. Try again in about {duration}.",
            actions=[ConditionalAccessStageAction(action_type=str(ConditionalAccessAction.LOCK_USER),
                                                  action_value={"lock_duration_seconds": 600}),
                    ConditionalAccessStageAction(action_type=str(ConditionalAccessAction.EMAIL_ADMIN),
                                                  action_value={"recipient": "admin@example.com"})])]
        db.session.add(policy)
        db.session.commit()

        with mock.patch("privacyidea.lib.conditional_access.engine._send_action_email", return_value=True):
            body = self._check({"user": "cornelius", "pass": "wrongpin"})
        self.assertEqual("wrong otp pin", body["detail"]["message"], body)
        self.assertFalse(is_user_locked(self.user))
        # The mail did go out, so that much is history; the lock that never happened is not.
        entries = get_authentication_logs()
        self.assertListEqual([str(ConditionalAccessAction.EMAIL_ADMIN)],
                             [outcome.action_type for outcome in get_outcomes(entries[-1].id)])

    def test_dry_run_lock_policy_persists_outcome_but_never_locks(self):
        # A dry-run LOCK_USER policy never locks the user, but its triggering request's authentication_log row records
        # what the policy would have done.
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=3, duration=600, dry_run=True)

        for _ in range(3):
            body = self._check({"user": "cornelius", "pass": "pin000000"})
            self.assertFalse(body["result"]["value"], body)

        entries = get_authentication_logs()
        self.assertEqual([AuthEventType.MFA_FAIL] * 3, [entry.event_type for entry in entries])
        # Never actually enforced.
        self.assertFalse(is_user_locked(self.user))

        # The triggering (third) request's row carries the dry-run outcome end to end: the engine returned an outcome
        # and the request context recorded it against the row it judged.
        outcomes = get_outcomes(entries[-1].id)
        self.assertEqual(1, len(outcomes))
        outcome = outcomes[0]
        self.assertTrue(outcome.dry_run)
        self.assertEqual("ca_lock", outcome.policy_name)
        self.assertEqual(3, outcome.threshold)
        self.assertEqual(3, outcome.event_count)
        self.assertEqual(str(ConditionalAccessAction.LOCK_USER), outcome.action_type)
        # The expiry the lock would have had, so a dry run reads like the enforced one.
        self.assertIn("expires_at", outcome.info)
        # The earlier rows, which did not trip the threshold, carry nothing.
        self.assertListEqual([], list(get_outcomes(entries[0].id)))

        # The user can still authenticate normally afterward -- never actually locked.
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)

    def test_lock_write_does_not_corrupt_transaction(self):
        # The engine writes each action inside its own guarded transaction on the conditional-access session (not the
        # shared request session), so a request that writes more than once never raises a transaction error. Two
        # policies tripping in one request force a second write; this asserts the post-eval helper's logger stays quiet
        # through the full /validate/check flow. A per-user lock (threshold 1) and a source-IP block (threshold 3
        # distinct users) are configured so cornelius's single failing request, as the third distinct user on the
        # pre-sprayed IP, trips both at once.
        ip = "203.0.113.9"
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=1, duration=600, priority=1)
        self._make_block_ip_policy(counter_type=AuthEventType.MFA_FAIL, threshold=3, duration=900, priority=2)
        _seed_ip_spray(self.user, AuthEventType.MFA_FAIL, ip, n_users=2)
        with self.assertNoLogs("privacyidea.api.lib.utils", level="WARNING"):
            body = self._check({"user": "cornelius", "pass": "pin000000"}, remote_addr=ip)
            self.assertFalse(body["result"]["value"], body)
        # Both policies' writes landed and the transaction was never corrupted.
        self.assertTrue(is_user_locked(self.user))
        self.assertTrue(is_ip_blocked(ip))

    def test_lock_fires_once_at_exact_threshold(self):
        # A LOCK action fires once, exactly at its threshold: once expired, failures that push the count above threshold
        # 3 do not re-fire the same stage. A successful login resets the count, so climbing back to exactly 3 re-locks.
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=3, duration=600)
        for _ in range(3):
            self.assertFalse(is_user_locked(self.user))
            self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertTrue(is_user_locked(self.user))

        # The lock runs out while the original failures are still in the window.
        state = db.session.get(UserLockState,
                               (self.user.resolver, self.user.uid, self.user.realm))
        state.lock_expires_at = utc_now() - timedelta(seconds=10)
        db.session.commit()
        self.assertFalse(is_user_locked(self.user))

        # A further failure pushes the count to 4, past the threshold-3 stage, so it does not re-fire and the user stays
        # unlocked.
        body = self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertFalse(body["result"]["value"], body)
        self.assertFalse(is_user_locked(self.user))

        # A successful login resets the counter; climbing back to exactly 3 re-locks.
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)
        for _ in range(3):
            self.assertFalse(is_user_locked(self.user))
            self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertTrue(is_user_locked(self.user))

    def test_below_threshold_does_not_lock(self):
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=3, duration=600)
        for _ in range(2):
            self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertFalse(is_user_locked(self.user))
        # A subsequent valid authentication still succeeds.
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)

    def test_successful_login_resets_failure_count(self):
        # A completed login clears the accumulated failures, so the lock counts only failures made after the success and
        # a legitimate user who just logged in is not re-locked by a single later typo.
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=3, duration=600)
        # Two failures (below the threshold), then a valid authentication.
        for _ in range(2):
            self._check({"user": "cornelius", "pass": "pin000000"})
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)

        # Two more failures: without the reset this would reach 4 >= 3 and lock, but the reset means only these two
        # post-login failures count, so the user stays unlocked.
        for _ in range(2):
            self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertFalse(is_user_locked(self.user))

        # A third post-login failure reaches the threshold and locks.
        self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertTrue(is_user_locked(self.user))

    # --- BLOCK_IP -------------------------------------------------------------

    def test_blocked_ip_rejected_without_token_logic(self):
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        self.assertEqual(0, self._failcount())

        # Even valid credentials must be rejected while the source IP is blocked.
        body = self._check({"user": "cornelius", "pass": "pin755224"}, remote_addr="203.0.113.7")
        self.assertTrue(body["result"]["status"], body)
        self.assertFalse(body["result"]["value"], body)
        # Generic response: the detail says what any failed authentication says and nothing more. This is the
        # shape a rejection has, and the one a stage tripped mid-request has to match (see
        # test_a_challenge_that_trips_a_lock_is_refused_like_any_other_request).
        self.assertSetEqual({"message", "threadid"}, set(body["detail"]), body)
        self.assertEqual(str(GENERIC_AUTH_FAILURE), body["detail"]["message"], body)
        # No token logic ran; the rejection itself is what the log records, with the blocked IP on the row.
        self.assertEqual(0, self._failcount())
        entries = assert_authentication_log([AuthEventType.IP_BLOCKED])
        assert_authentication_log_entry(entries[AuthEventType.IP_BLOCKED], user=self.user,
                                        source_ip="203.0.113.7", peer_ip="203.0.113.7",
                                        source_ip_source="REMOTE_ADDR")

        # The block is per-IP: the same user from a clean IP still authenticates, since the valid OTP was never consumed
        # by the rejected request above.
        body = self._check({"user": "cornelius", "pass": "pin755224"}, remote_addr="198.51.100.9")
        self.assertTrue(body["result"]["value"], body)

    def test_expired_block_does_not_reject(self):
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() - timedelta(seconds=10)))
        db.session.commit()
        # An expired block is not a block: a valid authentication still succeeds.
        body = self._check({"user": "cornelius", "pass": "pin755224"}, remote_addr="203.0.113.7")
        self.assertTrue(body["result"]["value"], body)
        # The stale row carries no state; the pre-check deletes it on this request from the IP rather than waiting for
        # the bulk purge command.
        self.assertIsNone(db.session.get(BlockList, "203.0.113.7"))

    def test_ip_blocked_after_spraying_distinct_users(self):
        # An IP that fails against many distinct users (spraying) trips a BLOCK_IP stage, while a single user's own
        # repeated failures from it never would.
        self._make_block_ip_policy(counter_type=AuthEventType.MFA_FAIL, threshold=3, duration=600)
        attacker_ip = "203.0.113.7"
        # Two other users already sprayed from this IP (below the threshold of 3).
        _seed_ip_spray(self.user, AuthEventType.MFA_FAIL, attacker_ip, n_users=2)
        # cornelius is the third distinct user: his failing request trips the block.
        body = self._check({"user": "cornelius", "pass": "pin000000"}, remote_addr=attacker_ip)
        self.assertFalse(body["result"]["value"], body)

        self.assertTrue(is_ip_blocked(attacker_ip))
        # The user themselves is not locked - only the IP was blocked.
        self.assertFalse(is_user_locked(self.user))

        # The next request from that IP is rejected by the pre-check, even with valid credentials.
        logs_before = len(get_authentication_logs())
        body = self._check({"user": "cornelius", "pass": "pin755224"}, remote_addr=attacker_ip)
        self.assertFalse(body["result"]["value"], body)
        self.assertListEqual([AuthEventType.IP_BLOCKED], _rows_since(logs_before))

    def test_escalation_to_permanent_lock_after_lock_expiry(self):
        # Escalation across two user policies (a temp lock at threshold 2, then PERMANENT_LOCK_USER at threshold 3) only
        # happens once the temp lock expires, because attempts made while locked are rejected at the pre-check and never
        # counted. A policy's priority does not preempt the temp lock: lock and block policies both fire once their
        # thresholds are met, regardless of priority order.
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=2, duration=60)
        create_conditional_access_policy(
            name="ca_permlock", time_window_seconds=3600,
            counter_types_to_track=_counter_types(AuthEventType.MFA_FAIL),
            stages=[{"failure_threshold": 3,
                     "actions": [{"action_type": str(ConditionalAccessAction.PERMANENT_LOCK_USER),
                             "action_value": None}]}],
            target=ConditionalAccessTarget.USER, priority=99)
        key = (self.user.resolver, self.user.uid, self.user.realm)

        # Two failures -> temp-locked, not yet permanently locked (count 2 < 3).
        for _ in range(2):
            self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertTrue(is_user_locked(self.user))
        self.assertIsNotNone(db.session.get(UserLockState, key).lock_expires_at)  # timed

        # Hammering during the lock is rejected at the pre-check and logged as USER_LOCKED, a type no policy tracks, so
        # the MFA_FAIL count stays frozen at 2 and never escalates to the permanent lock.
        logs_locked = len(get_authentication_logs())
        for _ in range(3):
            body = self._check({"user": "cornelius", "pass": "pin000000"})
            self.assertFalse(body["result"]["value"], body)
        self.assertListEqual([AuthEventType.USER_LOCKED] * 3, _rows_since(logs_locked))
        self.assertEqual(2, len([entry for entry in get_authentication_logs()
                                 if entry.event_type == AuthEventType.MFA_FAIL]))
        self.assertIsNotNone(db.session.get(UserLockState, key).lock_expires_at)  # still timed

        # Expire the lock; the next failure reaches count 3 and escalates, permanently locking the user (lock_expires_at
        # is None).
        state = db.session.get(UserLockState, key)
        state.lock_expires_at = utc_now() - timedelta(seconds=10)
        db.session.commit()
        body = self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertFalse(body["result"]["value"], body)
        state = db.session.get(UserLockState, key)
        self.assertIsNotNone(state)
        self.assertIsNone(state.lock_expires_at)
        self.assertTrue(is_user_locked(self.user))

    # --- DENY -----------------------------------------------------------------

    def test_deny_policy_rejects_after_threshold(self):
        self._make_decision_policy(name="ca_deny", counter_type=AuthEventType.MFA_FAIL,
                                   threshold=3, action=ConditionalAccessAction.DENY)
        for _ in range(3):
            body = self._check({"user": "cornelius", "pass": "pin000000"})
            self.assertFalse(body["result"]["value"], body)
        self.assertEqual(3, len(get_authentication_logs()))

        # The 4th request, even with a valid OTP, is denied pre-auth as a stateless reject classified ACCESS_DENIED that
        # persists no lock.
        logs_before = len(get_authentication_logs())
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertFalse(body["result"]["value"], body)
        self.assertEqual(str(GENERIC_AUTH_FAILURE), body["detail"]["message"], body)
        self.assertListEqual([AuthEventType.ACCESS_DENIED], _rows_since(logs_before))
        self.assertFalse(is_user_locked(self.user))

    def test_condition_exempts_a_subject_from_a_deny(self):
        # An exemption is a condition on the denying policy itself: an always-met DENY that excludes this user's
        # realm never applies to them, so a valid login still succeeds.
        create_conditional_access_policy(
            name="ca_deny_except_realm", time_window_seconds=3600,
            counter_types_to_track=_counter_types(AuthEventType.MFA_FAIL),
            stages=[{"failure_threshold": 0,
                     "actions": [{"action_type": str(ConditionalAccessAction.DENY), "action_value": None}]}],
            conditions=[{"condition_type": str(ConditionType.USER_REALM),
                         "operator": str(ConditionOperator.NOT_IN),
                         "value": [self.user.realm]}],
            target=ConditionalAccessTarget.USER, priority=1)
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)

    # --- precedence: user lock > IP block > DENY decision ------------------------
    # The pre-checks run in a fixed order - persistent user lock, then persistent IP block, then the stateless DENY
    # decision - so the rejection names the restriction that is already persisted rather than the policy.
    # A DENY whose threshold is lower than a LOCK_USER threshold shadows the lock, because DENY'd requests write no log
    # row and the failure count freezes below the lock threshold.

    def test_lock_checked_before_deny(self):
        # A persistent lock and an always-met DENY are both present; the lock is checked first, so the log records
        # USER_LOCKED rather than the policy's ACCESS_DENIED.
        self._lock_user(utc_now() + timedelta(seconds=600))
        self._make_decision_policy(name="ca_deny", counter_type=AuthEventType.MFA_FAIL,
                                   threshold=0, action=ConditionalAccessAction.DENY, priority=1)
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertFalse(body["result"]["value"], body)
        self.assertEqual(str(GENERIC_AUTH_FAILURE), body["detail"]["message"], body)
        # Rejected by the lock pre-check: no token logic, and the log says which restriction did it.
        self.assertEqual(0, self._failcount())
        entries = assert_authentication_log([AuthEventType.USER_LOCKED])
        assert_authentication_log_entry(entries[AuthEventType.USER_LOCKED], user=self.user)

    def test_ip_block_checked_before_deny(self):
        # The IP block is also checked before the DENY decision.
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        self._make_decision_policy(name="ca_deny", counter_type=AuthEventType.MFA_FAIL,
                                   threshold=0, action=ConditionalAccessAction.DENY, priority=1)
        body = self._check({"user": "cornelius", "pass": "pin755224"}, remote_addr="203.0.113.7")
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.IP_BLOCKED])
        assert_authentication_log_entry(entries[AuthEventType.IP_BLOCKED], user=self.user,
                                        source_ip="203.0.113.7", peer_ip="203.0.113.7",
                                        source_ip_source="REMOTE_ADDR")

    def test_deny_with_lower_threshold_shadows_lock_policy(self):
        # A DENY threshold lower than a LOCK_USER threshold wins first: once met, every further request is rejected
        # pre-auth without writing a log row, so the failure count freezes below the lock threshold and the lock never
        # engages. This is intentional: the stateless DENY self-heals as failures age out of its window, whereas a
        # persistent lock would not.
        self._make_decision_policy(name="ca_deny", counter_type=AuthEventType.MFA_FAIL,
                                   threshold=3, action=ConditionalAccessAction.DENY, priority=1)
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=5, duration=600, priority=2)

        for _ in range(3):
            body = self._check({"user": "cornelius", "pass": "pin000000"})
            self.assertFalse(body["result"]["value"], body)
        self.assertEqual(3, len(get_authentication_logs()))

        # Further failing attempts are denied by the pre-check and logged as ACCESS_DENIED, a type no policy tracks, so
        # the tracked MFA_FAIL count stays at 3 and the LOCK_USER threshold of 5 is never reached.
        logs_before = len(get_authentication_logs())
        for _ in range(3):
            body = self._check({"user": "cornelius", "pass": "pin000000"})
            self.assertFalse(body["result"]["value"], body)
        self.assertListEqual([AuthEventType.ACCESS_DENIED] * 3, _rows_since(logs_before))
        self.assertEqual(3, len([entry for entry in get_authentication_logs()
                                 if entry.event_type == AuthEventType.MFA_FAIL]))
        self.assertFalse(is_user_locked(self.user))

    # --- /validate/triggerchallenge -------------------------------------------

    def _trigger_challenge(self, remote_addr: str | None = None, data: dict | None = None) -> dict:
        if not getattr(self, "at", None):
            self.authenticate()
        kwargs = {"environ_base": {"REMOTE_ADDR": remote_addr}} if remote_addr else {}
        with self.app.test_request_context('/validate/triggerchallenge', method='POST',
                                           data=data if data is not None else {"user": "cornelius"},
                                           headers={"Authorization": self.at}, **kwargs):
            response = self.app.full_dispatch_request()
            self.assertEqual(200, response.status_code, response)
            return response.json

    def test_triggerchallenge_locked_user_rejected(self):
        self._lock_user(utc_now() + timedelta(seconds=600))
        body = self._trigger_challenge()
        # Generic failure (no challenge triggered) and no token logic ran.
        self.assertFalse(body["result"]["value"], body)
        self.assertEqual(str(GENERIC_AUTH_FAILURE), body["detail"]["message"], body)
        # The rejection classifies the request, and - crucially - no challenge is created in the DB even though no
        # transaction id is returned.
        entries = assert_authentication_log([AuthEventType.USER_LOCKED])
        assert_authentication_log_entry(entries[AuthEventType.USER_LOCKED], user=self.user)
        self.assertEqual(0, db.session.query(Challenge).count())

    def test_triggerchallenge_locked_user_rejected_via_serial(self):
        # A serial-only trigger carries no user= parameter, so it is gated on the token owner - the same resolution
        # /validate/check uses. Without it an admin naming the token instead of its owner would push a prompt to a
        # locked user's phone, and the lock would only be discovered when they answered it.
        # The serial is confirmed to trigger first, so the rejection is provably the lock.
        body = self._trigger_challenge(data={"serial": self.serial})
        self.assertEqual(1, body["result"]["value"], body)
        self.assertEqual(1, len(get_challenges(serial=self.serial)))
        delete_challenges(serial=self.serial)
        rows = len(get_authentication_logs())

        self._lock_user(utc_now() + timedelta(seconds=600))
        body = self._trigger_challenge(data={"serial": self.serial})
        self.assertEqual(0, body["result"]["value"], body)
        self.assertEqual(str(GENERIC_AUTH_FAILURE), body["detail"]["message"], body)
        # Refused before any token work: the rejection classifies the request and no challenge is created.
        self.assertListEqual([AuthEventType.USER_LOCKED], _rows_since(rows))
        self.assertListEqual([], get_challenges(serial=self.serial))

    def test_triggerchallenge_blocked_ip_rejected(self):
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        body = self._trigger_challenge(remote_addr="203.0.113.7")
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.IP_BLOCKED])
        assert_authentication_log_entry(entries[AuthEventType.IP_BLOCKED], user=self.user,
                                        source_ip="203.0.113.7", peer_ip="203.0.113.7",
                                        source_ip_source="REMOTE_ADDR")

    def test_triggerchallenge_denied_by_policy_rejected(self):
        # A default-deny policy (threshold 0) rejects every request pre-auth.
        self._make_decision_policy(name="ca_deny", counter_type=AuthEventType.PIN_FAIL,
                                   threshold=0, action=ConditionalAccessAction.DENY)
        body = self._trigger_challenge()
        self.assertFalse(body["result"]["value"], body)
        entries = assert_authentication_log([AuthEventType.ACCESS_DENIED])
        assert_authentication_log_entry(entries[AuthEventType.ACCESS_DENIED], user=self.user)

    def test_triggerchallenge_no_token_event_feeds_engine(self):
        # With no challenge-capable token, triggering classifies NO_TOKEN, and a policy tracking NO_TOKEN locks the user
        # via the post-eval seam.
        remove_token(self.serial)
        self._make_lock_policy(counter_type=AuthEventType.NO_TOKEN, threshold=1, duration=600)
        self.assertFalse(is_user_locked(self.user))
        body = self._trigger_challenge()
        self.assertEqual(0, body["result"]["value"], body)
        self.assertListEqual([AuthEventType.NO_TOKEN],
                             [entry.event_type for entry in get_authentication_logs()])
        self.assertTrue(is_user_locked(self.user))

    # --- /validate/polltransaction --------------------------------------------

    def _poll(self, transaction_id: str, remote_addr: str | None = None) -> dict:
        kwargs = {"environ_base": {"REMOTE_ADDR": remote_addr}} if remote_addr else {}
        with self.app.test_request_context(f'/validate/polltransaction/{transaction_id}',
                                           method='GET', **kwargs):
            response = self.app.full_dispatch_request()
            self.assertEqual(200, response.status_code, response)
            return response.json

    def _create_hotp_challenge(self) -> str:
        """Trigger a real challenge for cornelius' HOTP token (owned by cornelius)
        via /validate/check and return its transaction_id."""
        set_policy(name="ca_cr", scope=SCOPE.AUTH, action=f"{PolicyAction.CHALLENGERESPONSE}=hotp")
        try:
            body = self._check({"user": "cornelius", "pass": "pin"})
            self.assertEqual("CHALLENGE", body["result"]["authentication"], body)
            return body["detail"]["transaction_id"]
        finally:
            delete_policy("ca_cr")

    def test_polltransaction_is_not_gated(self):
        # The one authentication-related endpoint conditional access deliberately does not gate. A poll is a status
        # read: it carries no authentication event, cannot advance a counter, and reveals only the challenge's own
        # status. Gating it replaced detail.challenge_status - the field a client acts on, and the only channel that
        # could tell a poller to stop - with a message no shipped client reads.
        #
        # So a locked owner and a blocked source IP both keep polling normally, and the lock is enforced where it
        # decides something: on the /validate/check that would complete the login (asserted at the end).
        transaction_id = self._create_hotp_challenge()
        self._lock_user(utc_now() + timedelta(seconds=600))
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        logs_before = len(get_authentication_logs())

        for label, kwargs in (("locked owner", {}), ("blocked source IP", {"remote_addr": "203.0.113.7"})):
            body = self._poll(transaction_id, **kwargs)
            # The polling contract holds: the status the client reads, not a rejection message.
            self.assertEqual("pending", body["detail"]["challenge_status"], f"{label}: {body}")
            self.assertNotIn("message", body["detail"], f"{label}: {body}")

        # Still no authentication-log row and no outcome: polling accumulates nothing, gated or not.
        self.assertListEqual([], _rows_since(logs_before))
        self.assertEqual(0, get_ca_session().query(ConditionalAccessOutcome).count())

        # And the lock does bite the moment the request actually authenticates something.
        refused = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertFalse(refused["result"]["value"], refused)
        self.assertEqual(str(GENERIC_AUTH_FAILURE), refused["detail"]["message"], refused)

    def test_enforced_deny_records_its_outcome_on_the_rejection_row(self):
        # The pre-check writes the ACCESS_DENIED row, and the DENY outcome the engine returned - buffered on the context
        # because no row existed yet at decision time - is recorded against it.
        self._make_decision_policy(name="ca_deny", counter_type=AuthEventType.MFA_FAIL,
                                   threshold=0, action=ConditionalAccessAction.DENY)
        body = self._check({"user": "cornelius", "pass": "pin755224"})
        self.assertFalse(body["result"]["value"], body)

        entries = get_authentication_logs()
        self.assertListEqual([AuthEventType.ACCESS_DENIED], [entry.event_type for entry in entries])
        outcomes = get_outcomes(entries[0].id)
        self.assertEqual(1, len(outcomes))
        self.assertEqual(str(ConditionalAccessAction.DENY), outcomes[0].action_type)
        self.assertEqual("ca_deny", outcomes[0].policy_name)
        self.assertFalse(outcomes[0].dry_run)

    def test_a_rejection_is_not_fed_back_into_the_engine(self):
        # A rejection must not be evaluated, since counting it would let the lock feed itself: the row exists, no policy
        # tracks its type, and the lock is unchanged by the rejected request.
        self._make_lock_policy(counter_type=AuthEventType.MFA_FAIL, threshold=1, duration=600)
        self._check({"user": "cornelius", "pass": "pin000000"})
        self.assertTrue(is_user_locked(self.user))
        locked_until = db.session.get(UserLockState, (self.user.resolver, self.user.uid,
                                                        self.user.realm)).lock_expires_at

        logs_before = len(get_authentication_logs())
        self._check({"user": "cornelius", "pass": "pin000000"})

        self.assertListEqual([AuthEventType.USER_LOCKED], _rows_since(logs_before))
        # The lock was neither refreshed nor escalated by its own rejection.
        self.assertEqual(locked_until, db.session.get(UserLockState, (self.user.resolver, self.user.uid,
                                                                        self.user.realm)).lock_expires_at)

    def test_polltransaction_does_not_write_authentication_log(self):
        # Polling must not write an authentication-log row, since the smartphone's answer is logged at /ttype/push and
        # logging here too would double-count; only the trigger row from creating the challenge should exist.
        transaction_id = self._create_hotp_challenge()
        logs_before = len(get_authentication_logs())
        body = self._poll(transaction_id)
        self.assertEqual("pending", body["detail"]["challenge_status"], body)
        self.assertEqual(logs_before, len(get_authentication_logs()))

    # The /ttype/push authentication-path pre-check (locked owner / blocked IP rejected, enrollment not gated) is
    # covered end-to-end with real signed push answers in tests/test_api_push_validate.py (test_18e / test_18f), since
    # the pre-check lives in the push token's _api_endpoint_post auth branch.

    # --- /validate/initialize --------------------------------------------------

    def _initialize(self, remote_addr: str | None = None) -> dict:
        kwargs = {"environ_base": {"REMOTE_ADDR": remote_addr}} if remote_addr else {}
        with self.app.test_request_context('/validate/initialize', method='POST',
                                           data={"type": "passkey"}, **kwargs):
            response = self.app.full_dispatch_request()
            self.assertEqual(200, response.status_code, response)
            return response.json

    def test_initialize_that_trips_a_block_hands_out_no_challenge(self):
        # /validate/initialize says result.value: false even on success, so it is the sharpest case for the rule
        # that a rejection carries the reason and nothing else: a stage tripped by its own CHALLENGE_TRIGGERED
        # event withdraws the passkey payload it was about to return. A source-IP policy, because the passkey
        # flow resolves nobody - there is no user to lock.
        self._set_relying_party_id()
        create_conditional_access_policy(
            name="ca_initialize_block", time_window_seconds=3600,
            counter_types_to_track=_counter_types(AuthEventType.CHALLENGE_TRIGGERED),
            stages=[{"failure_threshold": 1, "error_message": "Blocked. Try again in about {duration}.",
                     "actions": [{"action_type": str(ConditionalAccessAction.BLOCK_IP), "action_value": 600}]}],
            target=ConditionalAccessTarget.SOURCE_IP, count_mode=str(CountMode.PER_REQUEST), priority=1)

        body = self._initialize(remote_addr="203.0.113.7")
        self.assertFalse(body["result"]["value"], body)
        self.assertTrue(is_ip_blocked("203.0.113.7"))
        self.assertEqual("Blocked. Try again in about 10 minute(s).", body["detail"]["message"], body)
        # Refused, so the passkey challenge is not handed over: a blocked client gets the reason and nothing
        # else, exactly as it would from the pre-check on its next attempt.
        self.assertSetEqual({"message", "threadid"}, set(body["detail"]), body)

    def _set_relying_party_id(self) -> None:
        """The relying-party id the passkey challenge needs; without it the endpoint fails before creating one, which
        would let a gate test pass for the wrong reason."""
        set_policy("ca_rp_id", scope=SCOPE.ENROLL, action=f"{FIDO2PolicyAction.RELYING_PARTY_ID}=example.com")
        self.addCleanup(delete_policy, "ca_rp_id")

    def test_initialize_blocked_ip_rejected(self):
        self._set_relying_party_id()
        # Positive control: unblocked, the endpoint initializes a challenge and writes a trackable row that is userless
        # (the passkey flow resolves nobody) but carries the source IP, which is what a source-IP policy counts.
        body = self._initialize(remote_addr="203.0.113.7")
        self.assertIn("passkey", body["detail"], body)
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=None,
                                        source_ip="203.0.113.7", peer_ip="203.0.113.7",
                                        source_ip_source="REMOTE_ADDR",
                                        transaction_id=body["detail"]["transaction_id"])
        challenges_before = db.session.query(Challenge).count()

        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        body = self._initialize(remote_addr="203.0.113.7")
        # Generic reject, and the body never ran: no challenge payload leaks and no challenge is created.
        self.assertFalse(body["result"]["value"], body)
        self.assertEqual(str(GENERIC_AUTH_FAILURE), body["detail"]["message"], body)
        self.assertNotIn("transaction_id", body["detail"], body)
        self.assertEqual(challenges_before, db.session.query(Challenge).count())
        # The rejection replaces the CHALLENGE_TRIGGERED row this request would have written: only the first call's row
        # remains, and the second contributes an untrackable IP_BLOCKED one.
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED, AuthEventType.IP_BLOCKED],
                                            same_attempt=False)
        assert_authentication_log_entry(entries[AuthEventType.IP_BLOCKED], user=None,
                                        source_ip="203.0.113.7", peer_ip="203.0.113.7",
                                        source_ip_source="REMOTE_ADDR")

    def test_initialize_cannot_feed_the_counter_that_blocked_it(self):
        # /validate/initialize writes a trackable CHALLENGE_TRIGGERED row.
        self._set_relying_party_id()
        create_conditional_access_policy(
            name="ca_initialize_rate", time_window_seconds=3600,
            counter_types_to_track=_counter_types(AuthEventType.CHALLENGE_TRIGGERED),
            stages=[{"failure_threshold": 2,
                     "actions": [{"action_type": str(ConditionalAccessAction.BLOCK_IP), "action_value": 600}]}],
            target=ConditionalAccessTarget.SOURCE_IP, count_mode=str(CountMode.PER_REQUEST), priority=1)

        # The first call is counted: one trackable CHALLENGE_TRIGGERED row, below the threshold.
        body = self._initialize(remote_addr="203.0.113.7")
        first_transaction = body["detail"]["transaction_id"]
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED])
        assert_authentication_log_entry(entries[AuthEventType.CHALLENGE_TRIGGERED], user=None,
                                        source_ip="203.0.113.7", peer_ip="203.0.113.7",
                                        source_ip_source="REMOTE_ADDR",
                                        transaction_id=first_transaction)
        self.assertFalse(is_ip_blocked("203.0.113.7"))

        # The second reaches the threshold, so its post-eval writes the block; two separate requests count as two
        # attempts (same_attempt=False).
        body = self._initialize(remote_addr="203.0.113.7")
        entries = assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED] * 2, same_attempt=False)
        self.assertTrue(is_ip_blocked("203.0.113.7"))
        # This call both triggered a challenge and tripped the block, so it is answered as the rejection it became:
        # the challenge is withdrawn from the response (left to expire unanswered, not invalidated).
        self.assertNotIn("transaction_id", body["detail"], body)
        self.assertNotIn("passkey", body["detail"], body)
        # The transaction is taken from the row and then proved, rather than read out of the response: this call's
        # challenge was withdrawn from the body, and it cannot be looked up in the challenge store either, since a
        # passkey challenge carries no serial and an unfiltered get_challenges() returns nothing when the challenges
        # live in Redis (the cache is keyed by serial/transaction and cannot enumerate). So assert what identifies
        # it - a transaction of its own, not the first call's, naming a challenge that really was created.
        tripping_transaction = entries.all[1].transaction_id
        self.assertNotEqual(first_transaction, tripping_transaction, entries.all[1])
        self.assertTrue(get_challenges(transaction_id=tripping_transaction))
        assert_authentication_log_entry(entries.all[1], user=None, source_ip="203.0.113.7", peer_ip="203.0.113.7",
                                        source_ip_source="REMOTE_ADDR",
                                        transaction_id=tripping_transaction)

        for _ in range(3):
            self._initialize(remote_addr="203.0.113.7")
        # Every further call is turned away and classified IP_BLOCKED, which is untrackable by construction, so no third
        # CHALLENGE_TRIGGERED row ever joins the two that produced the block and the count cannot be refreshed by the
        # block's own traffic.
        assert_authentication_log([AuthEventType.CHALLENGE_TRIGGERED] * 2 + [AuthEventType.IP_BLOCKED] * 3,
                                  same_attempt=False)

    # --- serial-only lock-evasion (resolve owner before the pre-check) ---------

    def test_locked_user_rejected_via_serial(self):
        # A serial-only request (no user= parameter) is gated on the token owner, resolved from the serial before the
        # pre-check, so a locked user is rejected even without a user parameter. Confirm the credentials are valid
        # first, so the rejection is provably the lock.
        body = self._check({"serial": self.serial, "pass": "pin755224"})
        self.assertTrue(body["result"]["value"], body)
        logs_after_success = len(get_authentication_logs())

        self._lock_user(utc_now() + timedelta(seconds=600))
        body = self._check({"serial": self.serial, "pass": "pin755224"})
        self.assertFalse(body["result"]["value"], body)
        self.assertEqual(str(GENERIC_AUTH_FAILURE), body["detail"]["message"], body)
        # Rejected before any token work: the fail counter is unmoved and the rejection classifies the request.
        self.assertListEqual([AuthEventType.USER_LOCKED], _rows_since(logs_after_success))
        self.assertEqual(0, self._failcount())

    # --- two policies restricting the same subject in one request ---------------

    def _lock_policy_named(self, name, priority, message, duration, action=ConditionalAccessAction.LOCK_USER) -> None:
        create_conditional_access_policy(
            name=name, time_window_seconds=3600,
            counter_types_to_track=_counter_types(AuthEventType.PIN_FAIL),
            stages=[{"failure_threshold": 1, "error_message": message,
                     "actions": [{"action_type": str(action), "action_value": duration}]}],
            target=ConditionalAccessTarget.USER, priority=priority)

    def test_a_policy_restating_the_lock_does_not_replace_its_wording(self):
        # Two policies lock the same user for the same duration in one request, so the second changes nothing about
        # the restriction. Policies run in priority order, so the wording in force is the higher-priority one's -
        # and stays that way, rather than being replaced by a silence the second policy may well have chosen
        # deliberately.
        self._lock_policy_named("ca_worded", 1, "Locked. Try again in about {duration}.", 600)
        self._lock_policy_named("ca_silent", 2, None, 600)

        body = self._check({"user": "cornelius", "pass": "wrongpin"})
        self.assertEqual("Locked. Try again in about 10 minute(s).", body["detail"]["message"], body)
        self.assertEqual("Locked. Try again in about {duration}.", get_user_lock(self.user).error_message)
        # Only the write that took effect is history; the one that changed nothing is not.
        entries = get_authentication_logs()
        self.assertListEqual(["ca_worded"], [outcome.policy_name for outcome in get_outcomes(entries[-1].id)])

    def test_a_permanent_lock_restated_keeps_the_first_wording(self):
        # The same for two permanent locks, where there is no expiry to compare at all.
        self._lock_policy_named("ca_worded", 1, "Your account is locked.", None,
                                action=ConditionalAccessAction.PERMANENT_LOCK_USER)
        self._lock_policy_named("ca_silent", 2, None, None, action=ConditionalAccessAction.PERMANENT_LOCK_USER)

        body = self._check({"user": "cornelius", "pass": "wrongpin"})
        self.assertEqual("Your account is locked.", body["detail"]["message"], body)

    def test_a_stronger_lock_still_brings_its_own_wording(self):
        # Unchanged by the above: strengthening is not restating, so the policy that lengthens the lock describes
        # the lock it left behind - the message travels with the expiry.
        self._lock_policy_named("ca_short", 1, "Locked. Try again in about {duration}.", 600)
        self._lock_policy_named("ca_long", 2, "Locked for a while.", 3600)

        body = self._check({"user": "cornelius", "pass": "wrongpin"})
        self.assertEqual("Locked for a while.", body["detail"]["message"], body)
        self.assertAlmostEqual(3600, get_user_lock(self.user).seconds_remaining, delta=10)

    def test_a_weaker_lock_is_still_declined_wording_and_all(self):
        # And so is declining: the shorter lock neither shortens the restriction nor gets to describe it.
        self._lock_policy_named("ca_long", 1, "Locked for a while.", 3600)
        self._lock_policy_named("ca_short", 2, "Locked. Try again in about {duration}.", 600)

        body = self._check({"user": "cornelius", "pass": "wrongpin"})
        self.assertEqual("Locked for a while.", body["detail"]["message"], body)
        self.assertAlmostEqual(3600, get_user_lock(self.user).seconds_remaining, delta=10)

    def _block_policy_named(self, name, priority, message, duration,
                            action=ConditionalAccessAction.BLOCK_IP) -> None:
        create_conditional_access_policy(
            name=name, time_window_seconds=3600,
            counter_types_to_track=_counter_types(AuthEventType.PIN_FAIL),
            stages=[{"failure_threshold": 1, "error_message": message,
                     "actions": [{"action_type": str(action), "action_value": duration}]}],
            target=ConditionalAccessTarget.SOURCE_IP, count_mode=CountMode.PER_REQUEST, priority=priority)

    def test_a_policy_restating_the_block_does_not_replace_its_wording(self):
        # The source-IP counterpart: two policies block the same address for the same duration in one request, so
        # the second changes nothing and the higher-priority policy's wording - or its deliberate silence - stands.
        self._block_policy_named("ca_ip_worded", 1, "Blocked. Try again in about {duration}.", 600)
        self._block_policy_named("ca_ip_silent", 2, None, 600)

        body = self._check({"user": "cornelius", "pass": "wrongpin"}, remote_addr=BLOCKED_IP)
        self.assertEqual("Blocked. Try again in about 10 minute(s).", body["detail"]["message"], body)
        self.assertEqual("Blocked. Try again in about {duration}.", get_ip_block(BLOCKED_IP).error_message)
        # Only the write that took effect is history.
        entries = get_authentication_logs()
        self.assertListEqual(["ca_ip_worded"], [outcome.policy_name for outcome in get_outcomes(entries[-1].id)])

    def test_a_permanent_block_restated_keeps_the_first_wording(self):
        self._block_policy_named("ca_ip_worded", 1, "Access from your address is blocked.", None,
                                 action=ConditionalAccessAction.PERMANENT_BLOCK_IP)
        self._block_policy_named("ca_ip_silent", 2, None, None, action=ConditionalAccessAction.PERMANENT_BLOCK_IP)

        body = self._check({"user": "cornelius", "pass": "wrongpin"}, remote_addr=BLOCKED_IP)
        self.assertEqual("Access from your address is blocked.", body["detail"]["message"], body)

    def test_a_stronger_block_still_brings_its_own_wording(self):
        self._block_policy_named("ca_ip_short", 1, "Blocked. Try again in about {duration}.", 600)
        self._block_policy_named("ca_ip_long", 2, "Blocked for a while.", 3600)

        body = self._check({"user": "cornelius", "pass": "wrongpin"}, remote_addr=BLOCKED_IP)
        self.assertEqual("Blocked for a while.", body["detail"]["message"], body)
        self.assertAlmostEqual(3600, get_ip_block(BLOCKED_IP).seconds_remaining, delta=10)

    def test_a_weaker_block_is_still_declined_wording_and_all(self):
        self._block_policy_named("ca_ip_long", 1, "Blocked for a while.", 3600)
        self._block_policy_named("ca_ip_short", 2, "Blocked. Try again in about {duration}.", 600)

        body = self._check({"user": "cornelius", "pass": "wrongpin"}, remote_addr=BLOCKED_IP)
        self.assertEqual("Blocked for a while.", body["detail"]["message"], body)
        self.assertAlmostEqual(3600, get_ip_block(BLOCKED_IP).seconds_remaining, delta=10)

    # --- identity rewriting (legacy setrealm / mangle) --------------------------

    def _setrealm_to_realm2(self) -> User:
        """Rewrite realm1 -> realm2 for cornelius via the legacy AUTHZ setrealm action, and return the identity
        that then actually authenticates."""
        self.setUp_user_realm2()
        set_policy(name="ca_setrealm", scope=SCOPE.AUTHZ,
                   action=f"{PolicyAction.SETREALM}={self.realm2}", realm=self.realm1)
        return User("cornelius", self.realm2)

    def test_a_lock_on_the_rewritten_identity_is_enforced(self):
        # setrealm replaces request.User, and everything downstream - the token lookup, the authentication-log row,
        # and so every count and every lock - uses that new identity. The gate has to check the same one: gating on
        # the realm the client typed would leave the lock the engine writes unenforceable, and a locked user would
        # authenticate for as long as the rewrite is configured.
        rewritten = self._setrealm_to_realm2()
        init_token({"serial": "CA_HOTP2", "type": "hotp", "otpkey": self.otpkey, "pin": "pin"}, user=rewritten)
        try:
            # The credentials are good, so a refusal is provably the lock and nothing else.
            body = self._check({"user": "cornelius", "realm": self.realm1, "pass": "pin755224"})
            self.assertTrue(body["result"]["value"], body)

            self._lock_user(utc_now() + timedelta(seconds=600), user=rewritten)
            rows = len(get_authentication_logs())
            body = self._check({"user": "cornelius", "realm": self.realm1, "pass": "pin287082"})
            self.assertFalse(body["result"]["value"], body)
            self.assertEqual(str(GENERIC_AUTH_FAILURE), body["detail"]["message"], body)
            self.assertListEqual([AuthEventType.USER_LOCKED], _rows_since(rows))
        finally:
            remove_token("CA_HOTP2")
            delete_policy("ca_setrealm")

    def test_a_lock_on_the_typed_identity_does_not_refuse_a_login_that_happens_elsewhere(self):
        # The other direction. The realm the client typed is not the one authenticating, and the engine never
        # writes a lock there - so one that exists was put there by something else, and must not turn away a login
        # it says nothing about.
        rewritten = self._setrealm_to_realm2()
        init_token({"serial": "CA_HOTP2", "type": "hotp", "otpkey": self.otpkey, "pin": "pin"}, user=rewritten)
        try:
            self._lock_user(utc_now() + timedelta(seconds=600))
            self.assertTrue(is_user_locked(self.user))
            self.assertFalse(is_user_locked(rewritten))
            body = self._check({"user": "cornelius", "realm": self.realm1, "pass": "pin755224"})
            self.assertTrue(body["result"]["value"], body)
        finally:
            remove_token("CA_HOTP2")
            delete_policy("ca_setrealm")

    # --- deferred write: one row per request, written at teardown ---------------

    def test_one_row_per_request_when_a_post_policy_corrects_the_outcome(self):
        # The authorized=deny post-policy runs after check() classifies the request; since the row is written only at
        # teardown, the correction amends the staged event instead of adding or re-writing a row, so exactly one row
        # carries the corrected classification.
        set_policy("authz_deny", scope=SCOPE.AUTHZ, action=f"{PolicyAction.AUTHORIZED}={AUTHORIZED.DENY}")
        try:
            with self.app.test_request_context('/validate/check', method='POST',
                                               data={"user": "cornelius", "pass": "pin755224"}):
                response = self.app.full_dispatch_request()
                # authorized=deny raises ValidateError, which the error handler maps to 400.
                self.assertEqual(400, response.status_code, response)
        finally:
            delete_policy("authz_deny")

        entries = get_authentication_logs()
        self.assertEqual(1, len(entries))
        self.assertEqual(str(AuthEventType.NOT_AUTHORIZED), entries[0].event_type)

    def test_engine_evaluates_the_corrected_outcome_only(self):
        # Two policies track the pre-authz outcome and the corrected one respectively; only the corrected outcome may be
        # evaluated.
        create_conditional_access_policy(
            name="ca_on_success", time_window_seconds=3600,
            counter_types_to_track=_counter_types(AuthEventType.LOGIN_SUCCESS),
            stages=[{"failure_threshold": 1,
                     "actions": [{"action_type": str(ConditionalAccessAction.PERMANENT_LOCK_USER),
                             "action_value": None}]}],
            target=ConditionalAccessTarget.USER, priority=1)
        set_policy("authz_deny", scope=SCOPE.AUTHZ, action=f"{PolicyAction.AUTHORIZED}={AUTHORIZED.DENY}")
        try:
            with self.app.test_request_context('/validate/check', method='POST',
                                               data={"user": "cornelius", "pass": "pin755224"}):
                self.app.full_dispatch_request()
        finally:
            delete_policy("authz_deny")

        # The row says NOT_AUTHORIZED, so the LOGIN_SUCCESS policy never saw a matching event and did not lock.
        self.assertFalse(is_user_locked(self.user))

    def test_a_conditional_access_rejection_is_not_reclassified_by_authz_deny(self):
        # The gate is the innermost decorator, so authorized=deny still runs on its rejection response; the rejection
        # row is the only record of why the request was refused. Relabelling it to NOT_AUTHORIZED would take the refused
        # request past the CA_ENFORCEMENT_EVENT_TYPES guard and into the conditional-access counters, a lock feeding
        # itself, so the rejection stands and the post-policy logs nothing of its own.
        self._lock_user(utc_now() + timedelta(seconds=600))
        set_policy("authz_deny", scope=SCOPE.AUTHZ, action=f"{PolicyAction.AUTHORIZED}={AUTHORIZED.DENY}")
        try:
            with self.app.test_request_context('/validate/check', method='POST',
                                               data={"user": "cornelius", "pass": "pin755224"}):
                self.app.full_dispatch_request()
        finally:
            delete_policy("authz_deny")

        entries = get_authentication_logs()
        self.assertEqual(1, len(entries))
        self.assertEqual(str(AuthEventType.USER_LOCKED), entries[0].event_type)

    def test_row_is_written_even_when_the_view_raises(self):
        # Teardown runs whether or not the request succeeded, so a request that ends in an error still logs its event.
        body = self._check({"user": "cornelius", "pass": "wrongpin000000"})
        self.assertFalse(body["result"]["value"], body)
        self.assertEqual(1, len(get_authentication_logs()))


class ConditionalAccessAuthTestCase(MyApiTestCase):
    """The WebUI JWT login (/auth) is gated by the same conditional-access engine."""

    def setUp(self) -> None:
        super().setUp()
        self.setUp_user_realms()
        self.user = User("cornelius", self.realm1)
        self._clear()

    def tearDown(self) -> None:
        self._clear()
        super().tearDown()

    @staticmethod
    def _clear():
        for model in (ConditionalAccessOutcome, UserLockState, BlockList, ConditionalAccessStageAction,
                      ConditionalAccessPolicyStage, ConditionalAccessPolicyCondition,
                      ConditionalAccessPolicyCounterType, ConditionalAccessPolicy,
                      AuthenticationLog):
            db.session.query(model).delete()
        db.session.commit()

    def _auth(self, username, password, remote_addr=None, transaction_id=None):
        kwargs = {"environ_base": {"REMOTE_ADDR": remote_addr}} if remote_addr else {}
        data = {"username": username, "password": password}
        if transaction_id:
            data["transaction_id"] = transaction_id
        with self.app.test_request_context('/auth', method='POST', data=data, **kwargs):
            return self.app.full_dispatch_request()

    @staticmethod
    def _make_password_policy(*, threshold, duration=600, window=3600, priority=1):
        create_conditional_access_policy(
            name="ca_pw", time_window_seconds=window,
            counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
            stages=[{"failure_threshold": threshold,
                     "actions": [{"action_type": str(ConditionalAccessAction.LOCK_USER), "action_value": duration}]}],
            target=ConditionalAccessTarget.USER, priority=priority)

    @staticmethod
    def _make_dry_run_password_policy(*, threshold, duration=600, window=3600, priority=1):
        create_conditional_access_policy(
            name="ca_pw_dry", time_window_seconds=window,
            counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
            stages=[{"failure_threshold": threshold,
                     "actions": [{"action_type": str(ConditionalAccessAction.LOCK_USER), "action_value": duration}]}],
            target=ConditionalAccessTarget.USER, dry_run=True, priority=priority)

    def test_dry_run_outcome_persisted_on_auth_login(self):
        # /auth evaluates in-view, rather than at request teardown, so it can surface the engine's notices in its own
        # response. It flushes the staged row first because the outcome needs that row to exist, or a dry-run policy
        # tripped by a WebUI login would record nothing.
        self._make_dry_run_password_policy(threshold=2)

        for _ in range(2):
            res = self._auth("cornelius", "wrongpassword")
            self.assertEqual(401, res.status_code, res)

        entries = get_authentication_logs()
        self.assertEqual([AuthEventType.PASSWORD_FAIL] * 2, [entry.event_type for entry in entries])
        # Dry-run never enforces, so the login stays refused on credentials only.
        self.assertFalse(is_user_locked(self.user))

        # The triggering (second) request's row carries the outcome; since /auth flushes in-view and evaluates right
        # after, this also covers recording against a row written earlier in the same request.
        outcomes = get_outcomes(entries[-1].id)
        self.assertEqual(1, len(outcomes))
        self.assertTrue(outcomes[0].dry_run)
        self.assertEqual("ca_pw_dry", outcomes[0].policy_name)
        self.assertEqual(2, outcomes[0].threshold)
        self.assertEqual(str(ConditionalAccessAction.LOCK_USER), outcomes[0].action_type)

    @staticmethod
    def _make_decision_policy(*, name, threshold, action, priority=1, window=3600, error_message=None):
        create_conditional_access_policy(
            name=name, time_window_seconds=window,
            counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
            stages=[{"failure_threshold": threshold, "error_message": error_message,
                     "actions": [{"action_type": str(action), "action_value": None}]}],
            target=ConditionalAccessTarget.USER, priority=priority)

    @staticmethod
    def _make_block_ip_policy(*, threshold, duration=600, window=3600, priority=1, error_message=None):
        create_conditional_access_policy(
            name="ca_block_ip", time_window_seconds=window,
            counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
            stages=[{"failure_threshold": threshold, "error_message": error_message,
                     "actions": [{"action_type": str(ConditionalAccessAction.BLOCK_IP), "action_value": duration}]}],
            target=ConditionalAccessTarget.SOURCE_IP, priority=priority)

    def test_locked_user_rejected_silently_by_default(self):
        # Nothing is volunteered: with no message configured, a locked user is refused with the same generic
        # message as a wrong password, down to the absent severity hint - which would give the lock away on its own.
        # The error *id* does differ (AUTHENTICATE rather than AUTHENTICATE_WRONG_CREDENTIALS), which is deliberate:
        # calling this wrong credentials would be a claim about a credential nothing checked. A deployment that wants
        # the two indistinguishable down to the id sets hide_specific_error_message, which maps every failed login
        # here to AUTHENTICATE anyway - and without that policy privacyIDEA volunteers the real reason in
        # detail.message for ordinary failures regardless, so the id is not what a rejection is hiding behind.
        db.session.add(UserLockState(resolver=self.user.resolver, uid=self.user.uid, realm=self.user.realm,
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        res = self._auth("cornelius", "test")
        self.assertEqual(401, res.status_code, res)
        self.assertEqual(403, res.json["result"]["error"]["code"], res.json)
        self.assertEqual(GENERIC_AUTH_FAILURE, res.json["result"]["error"]["message"], res.json)
        self.assertNotIn("restriction", res.json.get("detail") or {}, res.json)
        # The login is still classified, so an admin can see why it failed even though the user cannot.
        entries = assert_authentication_log([AuthEventType.USER_LOCKED])
        assert_authentication_log_entry(entries[AuthEventType.USER_LOCKED], user=self.user)

    def test_the_rejection_joins_the_transaction_it_refused(self):
        # A passkey or push login answers its challenge at /auth carrying the transaction, so a rejection there
        # belongs to that attempt rather than starting one of its own - the same linkage /validate rejections get.
        self._lock_user()
        res = self._auth("cornelius", "test", transaction_id="0123456789")
        self.assertEqual(401, res.status_code, res)
        entries = assert_authentication_log([AuthEventType.USER_LOCKED])
        assert_authentication_log_entry(entries[AuthEventType.USER_LOCKED], user=self.user,
                                        transaction_id="0123456789")

    def test_a_silent_lock_says_nothing_a_wrong_password_does_not(self):
        # The silent default: a locked account volunteers nothing a wrong password would not. Compared end to end
        # rather than against a constant, so it holds however many places happen to build the generic failure.
        #
        # Everything a human or a client reads is identical - status, message, detail. The error *id* is
        # deliberately not: a rejection carries AUTHENTICATE because calling it AUTHENTICATE_WRONG_CREDENTIALS
        # would assert something about a credential that was never checked, and is usually false outright (a
        # locked user typing the right password is rejected too). Accepted knowingly: without
        # hide_specific_error_message privacyIDEA volunteers the real reason in detail.message for ordinary
        # failures anyway, so the id is not what a silent rejection is hiding behind - and with that policy on,
        # every failed login here is AUTHENTICATE and the two are identical again (asserted below).
        wrong = self._auth("cornelius", "wrongpassword")
        self.assertEqual(401, wrong.status_code, wrong)
        self._clear_authentication_log()

        db.session.add(UserLockState(resolver=self.user.resolver, uid=self.user.uid, realm=self.user.realm,
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        locked = self._auth("cornelius", "test")

        self.assertEqual(wrong.status_code, locked.status_code, locked.json)
        self.assertEqual(wrong.json["result"]["error"]["message"],
                         locked.json["result"]["error"]["message"], locked.json)
        # The detail too, not just the error: an empty detail against a populated one would give the
        # lock away as surely as the error message would - the severity hint is withheld for that reason.
        self.assertEqual(wrong.json.get("detail"), locked.json.get("detail"), locked.json)
        self.assertEqual(4031, wrong.json["result"]["error"]["code"], wrong.json)
        self.assertEqual(403, locked.json["result"]["error"]["code"], locked.json)

    def test_masking_makes_a_silent_lock_identical_again(self):
        # The id difference above closes under hide_specific_error_message, which maps every failed login here to
        # AUTHENTICATE - so a deployment that wants the two indistinguishable down to the last field has a way.
        from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
        from privacyidea.lib.policies.actions import PolicyAction
        set_policy(name="ca_hide", scope=SCOPE.AUTH, action=f"{PolicyAction.HIDE_SPECIFIC_ERROR_MESSAGE}")
        try:
            wrong = self._auth("cornelius", "wrongpassword")
            self._clear_authentication_log()
            db.session.add(UserLockState(resolver=self.user.resolver, uid=self.user.uid, realm=self.user.realm,
                                            lock_expires_at=utc_now() + timedelta(seconds=600)))
            db.session.commit()
            locked = self._auth("cornelius", "test")

            self.assertEqual(wrong.status_code, locked.status_code, locked.json)
            self.assertEqual(wrong.json["result"], locked.json["result"], locked.json)
            self.assertEqual(wrong.json.get("detail"), locked.json.get("detail"), locked.json)
            self.assertEqual(403, locked.json["result"]["error"]["code"], locked.json)
        finally:
            delete_policy("ca_hide")

    def test_locked_user_rejected_at_auth(self):
        db.session.add(UserLockState(resolver=self.user.resolver, uid=self.user.uid, realm=self.user.realm,
                                        lock_expires_at=utc_now() + timedelta(seconds=600),
                                        error_message="Your account is locked. Try again in about {duration}."))
        db.session.commit()
        # Correct userstore password, but the user is locked -> 401 carrying the configured error message.
        res = self._auth("cornelius", "test")
        self.assertEqual(401, res.status_code, res)
        self.assertEqual(403, res.json["result"]["error"]["code"], res.json)
        message = res.json["result"]["error"]["message"]
        self.assertIn("locked", message.lower(), message)
        # {duration} is rendered against the time left now, not stored pre-rendered.
        self.assertIn("minute", message.lower(), message)
        self.assertNotIn("{duration}", message, message)
        self.assertNotIn(str(GENERIC_AUTH_FAILURE), message, message)
        # No severity hint: the error message is the only thing the user is told.
        self.assertNotIn("restriction", res.json.get("detail") or {}, res.json)
        # The login is classified by its rejection, so the log says why it failed even though no credential was checked.
        entries = assert_authentication_log([AuthEventType.USER_LOCKED])
        assert_authentication_log_entry(entries[AuthEventType.USER_LOCKED], user=self.user)

    def test_lock_is_checked_before_the_auth_timelimit_prepolicy(self):
        # The pre-check must run ahead of every other pre-policy, because auth_timelimit writes a trackable
        # NOT_AUTHORIZED row when its limit is hit (prepolicy.auth_timelimit), and any pre-policy running first would
        # let a locked user's rejected logins keep feeding the counters that locked them - the one way a lock could
        # refresh itself from inside the lock.
        set_policy("ca_maxfail", scope=SCOPE.AUTHZ, action=f"{PolicyAction.AUTHMAXFAIL}=2/1m")
        self.addCleanup(delete_policy, "ca_maxfail")
        # Two failed logins put the classic time limit over its threshold (it counts the audit log).
        for _ in range(2):
            self.assertEqual(401, self._auth("cornelius", "wrongpassword").status_code)

        # Positive control: with no lock in force, the time limit is what refuses the next login, proving it is armed -
        # otherwise the assertion below would hold for the wrong reason.
        self._clear_authentication_log()
        self.assertEqual(401, self._auth("cornelius", "test").status_code)
        self.assertListEqual([AuthEventType.NOT_AUTHORIZED], _rows_since(0))

        # With the time limit still tripped and the user now locked, the lock is what refuses the login, and the row
        # records the lock rather than the time limit.
        db.session.add(UserLockState(resolver=self.user.resolver, uid=self.user.uid, realm=self.user.realm,
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        self._clear_authentication_log()
        self.assertEqual(401, self._auth("cornelius", "test").status_code)
        entries = assert_authentication_log([AuthEventType.USER_LOCKED])
        assert_authentication_log_entry(entries[AuthEventType.USER_LOCKED], user=self.user)

    @staticmethod
    def _clear_authentication_log() -> None:
        # Only the authentication log is cleared, never the audit log, since the classic AUTHMAXFAIL counts from the
        # audit log and clearing that would un-trip the very policy under test.
        db.session.query(AuthenticationLog).delete()
        db.session.commit()

    def test_permanently_locked_user_message_at_auth(self):
        # A permanent lock (no expiry) shows an error message written for one: no countdown to offer.
        custom_error_message = "Your account has been locked. Please contact your administrator."
        db.session.add(UserLockState(
            resolver=self.user.resolver, uid=self.user.uid, realm=self.user.realm, lock_expires_at=None,
            error_message=custom_error_message))
        db.session.commit()
        res = self._auth("cornelius", "test")
        self.assertEqual(401, res.status_code, res)
        self.assertEqual(403, res.json["result"]["error"]["code"], res.json)
        self.assertEqual(custom_error_message, res.json["result"]["error"]["message"])

    def test_blocked_ip_rejected_at_auth(self):
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() + timedelta(seconds=600),
                                 error_message="Your address is blocked. Try again in about {duration}."))
        db.session.commit()
        # Correct userstore password, but the source IP is blocked -> 401 carrying the block's error message.
        res = self._auth("cornelius", "test", remote_addr="203.0.113.7")
        self.assertEqual(401, res.status_code, res)
        self.assertEqual(403, res.json["result"]["error"]["code"], res.json)
        message = res.json["result"]["error"]["message"]
        self.assertIn("Your address is blocked. Try again in about", message, message)
        self.assertIn("minute", message.lower(), message)
        self.assertNotIn("account", message.lower(), message)
        self.assertNotIn(str(GENERIC_AUTH_FAILURE), message, message)
        entries = assert_authentication_log([AuthEventType.IP_BLOCKED])
        assert_authentication_log_entry(entries[AuthEventType.IP_BLOCKED], user=self.user,
                                        source_ip="203.0.113.7", peer_ip="203.0.113.7",
                                        source_ip_source="REMOTE_ADDR")

    def test_blocked_local_admin_is_recorded_as_such(self):
        # The role must survive the pre-check, which runs before /auth decides its admin/user branch, by reading the
        # flag before_request already resolved (g.resolved_user). Otherwise a blocked local admin - the recovery account
        # an operator would hunt for after locking themselves out with an IP policy - would be filed under regular
        # users, since a local admin has no resolver/uid/realm, only a login name.
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()

        res = self._auth(self.testadmin, self.testadminpw, remote_addr="203.0.113.7")
        self.assertEqual(401, res.status_code, res)

        entries = assert_authentication_log([AuthEventType.IP_BLOCKED])
        assert_authentication_log_entry(entries[AuthEventType.IP_BLOCKED], user=User(self.testadmin),
                                        source_ip="203.0.113.7", peer_ip="203.0.113.7",
                                        source_ip_source="REMOTE_ADDR", user_role=AuthLogUserRole.ADMIN_INTERNAL)

    def test_permanently_blocked_ip_message_at_auth(self):
        # A permanent block (no expiry) shows an error message written for one, with no countdown.
        custom_error_message = "Your address has been blocked. Please contact your administrator."
        db.session.add(BlockList(
            ip="203.0.113.7", block_expires_at=None,
            error_message=custom_error_message))
        db.session.commit()
        res = self._auth("cornelius", "test", remote_addr="203.0.113.7")
        self.assertEqual(401, res.status_code, res)
        self.assertEqual(403, res.json["result"]["error"]["code"], res.json)
        message = res.json["result"]["error"]["message"]
        self.assertEqual(custom_error_message, message)

    def test_hide_specific_error_message_leaves_the_configured_message_alone(self):
        # The two are separate concerns: that policy suppresses what privacyIDEA volunteers by default, while
        # this error message is something an admin wrote. So it is not the policy's to rewrite.
        from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
        from privacyidea.lib.policies.actions import PolicyAction
        db.session.add(UserLockState(resolver=self.user.resolver, uid=self.user.uid,
                                        realm=self.user.realm, lock_expires_at=None,
                                        error_message="MSG-ALPHA"))
        db.session.commit()
        set_policy(name="ca_hide", scope=SCOPE.AUTH, action=f"{PolicyAction.HIDE_SPECIFIC_ERROR_MESSAGE}")
        try:
            res = self._auth("cornelius", "test")
            self.assertEqual(401, res.status_code, res)
            self.assertEqual("MSG-ALPHA", res.json["result"]["error"]["message"], res.json)
        finally:
            delete_policy("ca_hide")

    def test_hide_specific_error_message_still_masks_a_silent_lock(self):
        # Nothing was configured, so there is no conditional-access error message to keep and the rejection is
        # masked with every other failed login.
        from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
        from privacyidea.lib.policies.actions import PolicyAction
        self._lock_user()
        set_policy(name="ca_hide", scope=SCOPE.AUTH, action=f"{PolicyAction.HIDE_SPECIFIC_ERROR_MESSAGE}")
        try:
            res = self._auth("cornelius", "test")
            self.assertEqual(401, res.status_code, res)
            self.assertEqual("Authentication failed.", res.json["result"]["error"]["message"], res.json)
        finally:
            delete_policy("ca_hide")

    def test_the_tripping_request_at_auth_carries_no_details(self):
        # What the token made of the credential no longer decides anything once a restriction is written, so
        # those details describe an overtaken attempt. The rejection carries the error message and nothing else.
        # Logging in against privacyIDEA rather than the resolver, so the failure carries the token layer's
        # own detail - the reason it refused, and what it refused with - for the restriction to overtake.
        from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
        from privacyidea.lib.policies.actions import PolicyAction
        set_policy("ca_pi_login", scope=SCOPE.WEBUI, action=f"{PolicyAction.LOGINMODE}=privacyIDEA")
        create_conditional_access_policy(
            name="ca_otp_msg", time_window_seconds=3600,
            counter_types_to_track=_counter_types(AuthEventType.NO_TOKEN),
            stages=[{"failure_threshold": 2, "error_message": "MSG-ALPHA",
                     "actions": [{"action_type": str(ConditionalAccessAction.LOCK_USER), "action_value": 600}]}],
            target=ConditionalAccessTarget.USER, priority=1)
        try:
            first = self._auth("cornelius", "wrongpin123456")
            self.assertEqual(401, first.status_code, first)
            # The ordinary failure says what the token layer made of it.
            self.assertIn("message", first.json.get("detail") or {}, first.json)

            tripping = self._auth("cornelius", "wrongpin123456")
            self.assertEqual(401, tripping.status_code, tripping)
            self.assertEqual("MSG-ALPHA", tripping.json["result"]["error"]["message"], tripping.json)
            self.assertFalse(tripping.json.get("detail"), tripping.json)
            self.assertTrue(is_user_locked(self.user))
        finally:
            delete_policy("ca_pi_login")

    def test_a_challenge_at_auth_that_trips_a_lock_is_refused_as_a_login_failure_is(self):
        # /auth hands back a challenge as a 200 and returns before it evaluates, so a restriction written on that
        # request reaches the response hook with a success-shaped body in hand. Editing it in place would answer
        # with value false and REJECT - a shape no failed login here ever has, and so the one field that would
        # identify a rejection. It has to be rendered as the error response every failure here is.
        init_token({"serial": "CA_AUTH_HOTP", "type": "hotp", "otpkey": self.otpkey, "pin": "pin"}, user=self.user)
        set_policy("ca_webui_login", scope=SCOPE.WEBUI, action=f"{PolicyAction.LOGINMODE}=privacyIDEA")
        set_policy("ca_cr", scope=SCOPE.AUTH, action=f"{PolicyAction.CHALLENGERESPONSE}=hotp")
        create_conditional_access_policy(
            name="ca_chal", time_window_seconds=3600,
            counter_types_to_track=[str(AuthEventType.CHALLENGE_TRIGGERED)],
            stages=[{"failure_threshold": 1, "error_message": None,
                     "actions": [{"action_type": str(ConditionalAccessAction.LOCK_USER), "action_value": 600}]}],
            target=ConditionalAccessTarget.USER, priority=1)
        try:
            tripping = self._auth("cornelius", "pin")
            self.assertEqual(401, tripping.status_code, tripping)
            self.assertEqual(Error.AUTHENTICATE, tripping.json["result"]["error"]["code"], tripping.json)
            self.assertTrue(is_user_locked(self.user))
            # The challenge goes with it: a transaction_id the next request would refuse is not handed out.
            self.assertFalse(tripping.json.get("detail"), tripping.json)

            # And it reads exactly as the rejection the lock produces from now on, which is the whole promise.
            refused = self._auth("cornelius", "pin")
            self.assertEqual(tripping.status_code, refused.status_code, refused.json)
            self.assertEqual(tripping.json["result"], refused.json["result"], refused.json)
            self.assertEqual(tripping.json.get("detail"), refused.json.get("detail"), refused.json)
        finally:
            remove_token("CA_AUTH_HOTP")
            delete_policy("ca_webui_login")
            delete_policy("ca_cr")

    def test_ip_block_trip_message_at_auth(self):
        # The failure that trips the BLOCK_IP stage (by crossing the distinct-user
        # threshold) already tells the user about the block instead of "Wrong
        # credentials".
        self._make_block_ip_policy(threshold=3, error_message="Blocked. Try again in about {duration}.")
        ip = "203.0.113.7"
        # Below the threshold, a failure is just a plain wrong-credentials rejection.
        res = self._auth("cornelius", "wrongpass", remote_addr=ip)
        self.assertEqual(401, res.status_code, res)
        self.assertEqual(str(GENERIC_AUTH_FAILURE), res.json["result"]["error"]["message"], res.json)
        # Two other users spray the same IP: with cornelius that is 3 distinct users.
        _seed_ip_spray(self.user, AuthEventType.PASSWORD_FAIL, ip, n_users=2)
        # cornelius's next failure crosses the distinct-user threshold -> IP blocked.
        res = self._auth("cornelius", "wrongpass", remote_addr=ip)
        self.assertEqual(401, res.status_code, res)
        message = res.json["result"]["error"]["message"]
        self.assertIn("Blocked. Try again in about", message, message)
        self.assertIn("minute", message.lower(), message)
        self.assertNotIn(str(GENERIC_AUTH_FAILURE), message, message)
        # The user themselves is not locked - only the IP was blocked.
        self.assertFalse(is_user_locked(self.user))

    def test_deny_policy_rejects_at_auth(self):
        # After enough prior PASSWORD_FAILs the next login is denied pre-auth, even with
        # the correct password. The message states it was a conditional-access decision
        # (without naming the policy); no new log row and no persisted lock.
        self._make_decision_policy(name="ca_deny", threshold=3, action=ConditionalAccessAction.DENY, error_message="MSG-DELTA")
        for _ in range(3):
            res = self._auth("cornelius", "wrongpass")
            self.assertEqual(401, res.status_code, res)
        logs_before = len(get_authentication_logs())
        res = self._auth("cornelius", "test")
        self.assertEqual(401, res.status_code, res)
        self.assertEqual(403, res.json["result"]["error"]["code"], res.json)
        message = res.json["result"]["error"]["message"]
        # A DENY persists nothing, so the error message is read live off the deciding stage.
        self.assertEqual("MSG-DELTA", message)
        self.assertListEqual([AuthEventType.ACCESS_DENIED], _rows_since(logs_before))
        self.assertFalse(is_user_locked(self.user))

    # --- precedence: user lock > IP block > DENY decision ------------------------
    # The /auth pre-checks run in the same fixed order as /validate/check - persistent user lock, then persistent IP
    # block, then the stateless DENY decision - directly observable through the distinct 401 messages: "account" for
    # the lock, the IP for the block, "conditional-access" for the decision.

    def _lock_user(self, error_message=None):
        db.session.add(UserLockState(resolver=self.user.resolver, uid=self.user.uid, realm=self.user.realm,
                                        lock_expires_at=utc_now() + timedelta(seconds=600),
                                        error_message=error_message))
        db.session.commit()

    def _block_ip(self, ip, error_message=None):
        db.session.add(BlockList(ip=ip, block_expires_at=utc_now() + timedelta(seconds=600),
                                 error_message=error_message))
        db.session.commit()

    def test_lock_checked_before_deny_at_auth(self):
        # Both a persistent lock and an always-met DENY stage: the lock is checked
        # first, so the 401 states the account lockout, not the policy denial.
        self._lock_user(error_message="MSG-ALPHA")
        self._make_decision_policy(name="ca_deny", threshold=0, action=ConditionalAccessAction.DENY,
                                   error_message="MSG-DELTA")
        res = self._auth("cornelius", "test")
        self.assertEqual(401, res.status_code, res)
        message = res.json["result"]["error"]["message"]
        self.assertEqual("MSG-ALPHA", message)

    def test_ip_block_checked_before_deny_at_auth(self):
        # Both a persistent IP block and an always-met DENY stage: the block is
        # checked first, so the 401 names the blocked IP, not the policy denial.
        self._block_ip("203.0.113.7", error_message="MSG-BETA")
        self._make_decision_policy(name="ca_deny", threshold=0, action=ConditionalAccessAction.DENY,
                                   error_message="MSG-DELTA")
        res = self._auth("cornelius", "test", remote_addr="203.0.113.7")
        self.assertEqual(401, res.status_code, res)
        message = res.json["result"]["error"]["message"]
        self.assertEqual("MSG-BETA", message)

    def test_both_restrictions_are_reported_at_auth(self):
        # A lock and an IP block are independent facts, resolved differently, so both are stated - telling
        # the user about one would leave them to discover the other by failing again. Equally severe here,
        # so the lock leads, matching the order they are checked in.
        self._lock_user(error_message="MSG-ALPHA")
        self._block_ip("203.0.113.7", error_message="MSG-BETA")
        res = self._auth("cornelius", "test", remote_addr="203.0.113.7")
        self.assertEqual(401, res.status_code, res)
        message = res.json["result"]["error"]["message"]
        self.assertEqual("MSG-ALPHA MSG-BETA", message)

    def test_permanent_ip_block_is_reported_before_a_timed_lock(self):
        # Escalation case: the user is temp-locked (1 min) AND their IP is now
        # permanently blocked. The rejection must report the permanent block - the
        # longer-lasting (binding) restriction - not "try again in a minute", which
        # would be misleading since waiting it out cannot help.
        self._lock_user(error_message="MSG-ALPHA")  # timed user lock, 600s
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=None,
                                 error_message="MSG-GAMMA"))
        db.session.commit()
        res = self._auth("cornelius", "test", remote_addr="203.0.113.7")
        self.assertEqual(401, res.status_code, res)
        message = res.json["result"]["error"]["message"]
        # The permanent block leads: waiting out the lock cannot help, so that is what the user needs first.
        self.assertEqual("MSG-GAMMA MSG-ALPHA", message)

    def test_permanent_lock_is_reported_before_a_timed_ip_block(self):
        # Symmetric: a permanent user lock outranks a timed IP block.
        db.session.add(UserLockState(resolver=self.user.resolver, uid=self.user.uid, realm=self.user.realm,
                                        lock_expires_at=None, error_message="MSG-ALPHA"))
        self._block_ip("203.0.113.7", error_message="MSG-BETA")  # timed block, 600s
        res = self._auth("cornelius", "test", remote_addr="203.0.113.7")
        self.assertEqual(401, res.status_code, res)
        message = res.json["result"]["error"]["message"]
        # Symmetric: the permanent lock leads, the timed block follows.
        self.assertEqual("MSG-ALPHA MSG-BETA", message)

    def test_the_same_error_message_on_a_lock_and_a_block_is_said_once(self):
        # One generic sentence, configured on a user stage and on a source-IP stage. Both restrictions are in force
        # and both are still reported - the rejection just does not say the same thing twice, exactly as the
        # post-response evaluation does not for two policies locking the same user.
        db.session.add(UserLockState(resolver=self.user.resolver, uid=self.user.uid, realm=self.user.realm,
                                        lock_expires_at=None, error_message="MSG-ALPHA"))
        db.session.add(BlockList(ip="203.0.113.7", block_expires_at=None, error_message="MSG-ALPHA"))
        db.session.commit()
        res = self._auth("cornelius", "test", remote_addr="203.0.113.7")
        self.assertEqual(401, res.status_code, res)
        self.assertEqual("MSG-ALPHA", res.json["result"]["error"]["message"])

    def test_user_locked_after_password_failures(self):
        self._make_password_policy(threshold=3)
        for _ in range(3):
            res = self._auth("cornelius", "wrongpass")
            self.assertEqual(401, res.status_code, res)
        self.assertTrue(is_user_locked(self.user))

        # The correct password is now also rejected, proving the lock rather than a credential check, and the log
        # records the lock as the reason rather than a password failure.
        logs_before = len(get_authentication_logs())
        res = self._auth("cornelius", "test")
        self.assertEqual(401, res.status_code, res)
        self.assertListEqual([AuthEventType.USER_LOCKED], _rows_since(logs_before))

    def test_the_error_id_follows_what_the_response_is_about(self):
        # AUTHENTICATE_WRONG_CREDENTIALS is a claim about the credential, so it is kept exactly where that claim
        # holds and dropped where it does not. The line is the one compose_failure_message already draws for the
        # message, so the id and the wording can never describe different things.

        # An ordinary failure: the credential was wrong and nothing else happened.
        ordinary = self._auth("cornelius", "wrongpass")
        self.assertEqual(4031, ordinary.json["result"]["error"]["code"], ordinary.json)
        self._clear()

        # A stage that trips silently still *restricted* this login, so it is answered as the rejection it became -
        # generic wording, no details, generic id - identically to the logins the lock then refuses. Whether an
        # admin configured wording changes what is said, never whether this was a rejection.
        self._make_password_policy(threshold=2)
        self._auth("cornelius", "wrongpass")
        silent = self._auth("cornelius", "wrongpass")
        self.assertTrue(is_user_locked(self.user))
        self.assertEqual(403, silent.json["result"]["error"]["code"], silent.json)
        self.assertEqual(str(GENERIC_AUTH_FAILURE), silent.json["result"]["error"]["message"], silent.json)
        self._clear()

        # With wording the response *is* about the restriction - it says so - so it takes the generic id.
        create_conditional_access_policy(
            name="ca_pw_worded", time_window_seconds=3600,
            counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
            stages=[{"failure_threshold": 2, "error_message": "Locked for {duration}.",
                     "actions": [{"action_type": str(ConditionalAccessAction.LOCK_USER), "action_value": 600}]}],
            target=ConditionalAccessTarget.USER, priority=1)
        self._auth("cornelius", "wrongpass")
        worded = self._auth("cornelius", "wrongpass")
        self.assertTrue(is_user_locked(self.user))
        self.assertEqual(403, worded.json["result"]["error"]["code"], worded.json)

        # And every request after it is refused by the pre-check, which never looked at a credential at all - the
        # case where AUTHENTICATE_WRONG_CREDENTIALS would be false outright. The correct password proves it.
        after = self._auth("cornelius", "test")
        self.assertEqual(403, after.json["result"]["error"]["code"], after.json)

    @smtpmock.activate
    def test_email_notice_surfaced_in_auth_rejection(self):
        # When an EMAIL_* action fires on the failing request, its notice is appended to the
        # rejection message so the login screen shows it, just like a lock message.
        smtpmock.setdata(response={})
        add_smtpserver(identifier="actionmail", server="1.2.3.4", tls=False)
        try:
            create_conditional_access_policy(
                name="ca_mail", time_window_seconds=3600,
                counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
                stages=[{"failure_threshold": 2, "error_message": "MSG-DELTA",
                         "actions": [{"action_type": str(ConditionalAccessAction.EMAIL_ADMIN),
                                      "action_value": {"smtp_identifier": "actionmail",
                                                       "recipient_group": "soc@example.com",
                                                       "subject": "alert", "body": "alert"}}]}],
                target=ConditionalAccessTarget.USER, priority=1)

            # 1st failure is below the threshold: plain rejection, no email, nothing surfaced.
            res = self._auth("cornelius", "wrongpass")
            self.assertEqual(401, res.status_code, res)
            self.assertEqual(str(GENERIC_AUTH_FAILURE), res.json["result"]["error"]["message"])

            # 2nd failure trips the stage: the email goes out and the stage's own error message rides back on
            # the 401. A notify-only stage leaves no lock row, so this is the one path where the message
            # travels with the evaluation rather than being read off a restriction.
            res = self._auth("cornelius", "wrongpass")
            self.assertEqual(401, res.status_code, res)
            # Appended to the ordinary failure, not replacing it: the credential failure is still the reason.
            # compose_failure_message strips the reason's own full stop before joining, so the two sentences
            # are separated by exactly one.
            self.assertEqual(f"{str(GENERIC_AUTH_FAILURE).rstrip('.')}. MSG-DELTA",
                             res.json["result"]["error"]["message"])
            self.assertEqual(["soc@example.com"], smtpmock.get_sent_recipient())
            # An EMAIL-only stage writes no lock state, so the pre-check still lets the user in.
            self.assertFalse(is_user_locked(self.user))
        finally:
            delete_smtpserver("actionmail")

    @smtpmock.activate
    def test_the_policy_supplies_a_notify_only_stage_its_error_message(self):
        # The fallback is not restrictions only: a stage that merely notified describes itself too, from the
        # standard error message for the actions that actually ran. Appended to the failure, because a notification
        # is not why the request was refused - the credential still is.
        from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
        from privacyidea.lib.policies.actions import PolicyAction
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        set_policy(name="ca_show", scope=SCOPE.CONDITIONAL_ACCESS,
                   action=f"{PolicyAction.SHOW_DEFAULT_CA_ERROR_MESSAGE}")
        try:
            create_conditional_access_policy(
                name="ca_mail_generic", time_window_seconds=3600,
                counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
                # No error_message: the stage says nothing of its own, so the policy speaks for it.
                stages=[{"failure_threshold": 2, "actions": [{"action_type": str(ConditionalAccessAction.EMAIL_ADMIN),
                                      "action_value": {"smtp_identifier": "lockoutmail",
                                                       "recipient_group": "soc@example.com",
                                                       "subject": "alert", "body": "alert"}}]}],
                target=ConditionalAccessTarget.USER, priority=1)

            self._auth("cornelius", "wrongpass")
            res = self._auth("cornelius", "wrongpass")
            self.assertEqual(401, res.status_code, res)
            expected = f"{str(GENERIC_AUTH_FAILURE).rstrip('.')}. {default_error_message(ConditionalAccessAction.EMAIL_ADMIN)}"
            self.assertEqual(expected, res.json["result"]["error"]["message"], res.json)
            self.assertListEqual(["soc@example.com"], smtpmock.get_sent_recipient())
            # Still only a notification, so nothing was restricted and the details are the failure's own.
            self.assertFalse(is_user_locked(self.user))
        finally:
            delete_policy("ca_show")
            delete_smtpserver("lockoutmail")

    @smtpmock.activate
    def test_lock_message_and_email_notice_combined(self):
        # A stage that both locks the user (timed) and emails the admin leads the locking request's rejection with the
        # lock message and appends the email notice.
        smtpmock.setdata(response={})
        add_smtpserver(identifier="actionmail", server="1.2.3.4", tls=False)
        try:
            create_conditional_access_policy(
                name="ca_lockmail", time_window_seconds=3600,
                counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
                stages=[{"failure_threshold": 2, "error_message": "Locked for {duration}. Your administrator has been notified.",
                         "actions": [{"action_type": str(ConditionalAccessAction.LOCK_USER), "action_value": 600},
                                     {"action_type": str(ConditionalAccessAction.EMAIL_ADMIN),
                                      "action_value": {"smtp_identifier": "actionmail",
                                                       "recipient_group": "soc@example.com",
                                                       "subject": "s", "body": "b"}}]}],
                target=ConditionalAccessTarget.USER, priority=1)

            self._auth("cornelius", "wrongpass")  # 1st failure: below the threshold
            res = self._auth("cornelius", "wrongpass")  # 2nd: trips the stage -> lock + email
            self.assertEqual(401, res.status_code, res)
            message = res.json["result"]["error"]["message"]
            # One message, written by the admin to cover both facts, carried by the lock row. The stage
            # does not also contribute it through the evaluation, or the user would be told twice.
            self.assertIn("Locked for", message, message)
            self.assertIn("minute", message.lower(), message)
            self.assertEqual(1, message.count("administrator has been notified"), message)
            self.assertNotIn(str(GENERIC_AUTH_FAILURE), message, message)
            self.assertTrue(is_user_locked(self.user))
        finally:
            delete_smtpserver("actionmail")

    @smtpmock.activate
    def test_the_policy_describes_every_action_a_stage_ran(self):
        # A stage that locks and notifies at once. With wording of its own an admin covers both facts in one
        # sentence; falling back to the standard wording has to cover them too, or the user is told about the
        # lock and left to discover the email.
        from privacyidea.lib.policy import set_policy, delete_policy, SCOPE
        from privacyidea.lib.policies.actions import PolicyAction
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        set_policy(name="ca_show", scope=SCOPE.CONDITIONAL_ACCESS,
                   action=f"{PolicyAction.SHOW_DEFAULT_CA_ERROR_MESSAGE}")
        try:
            create_conditional_access_policy(
                name="ca_lockmail_generic", time_window_seconds=3600,
                counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
                # No error_message: the policy speaks for the stage, for every action it runs.
                stages=[{"failure_threshold": 2, "actions": [{"action_type": str(ConditionalAccessAction.LOCK_USER), "action_value": 600},
                                     {"action_type": str(ConditionalAccessAction.EMAIL_ADMIN),
                                      "action_value": {"smtp_identifier": "lockoutmail",
                                                       "recipient_group": "soc@example.com",
                                                       "subject": "s", "body": "b"}}]}],
                target=ConditionalAccessTarget.USER, priority=1)

            self._auth("cornelius", "wrongpass")
            res = self._auth("cornelius", "wrongpass")
            self.assertEqual(401, res.status_code, res)
            message = res.json["result"]["error"]["message"]
            self.assertTrue(is_user_locked(self.user))
            self.assertEqual(["soc@example.com"], smtpmock.get_sent_recipient())
            lock = str(default_error_message(ConditionalAccessAction.LOCK_USER)).replace("{duration}", "10 minute(s)")
            self.assertIn(lock, message, message)
            self.assertIn(str(default_error_message(ConditionalAccessAction.EMAIL_ADMIN)), message, message)
        finally:
            delete_policy("ca_show")
            delete_smtpserver("lockoutmail")

    def test_break_glass_local_admin_is_exempt_from_pre_auth_deny(self):
        # A blanket source-IP DENY exempts local admins; it must target source_ip, since a user-target policy already
        # skips a local admin because their User() never resolves and the role would never be consulted. Loopback is on
        # the never-block list, hence the test uses 10.0.0.5.
        create_conditional_access_policy(
            name="ca_deny_ip", time_window_seconds=3600,
            counter_types_to_track=_counter_types(AuthEventType.PASSWORD_FAIL),
            stages=[{"failure_threshold": 0, "error_message": "MSG-DELTA",
                     "actions": [{"action_type": str(ConditionalAccessAction.DENY), "action_value": None}]}],
            conditions=[{"condition_type": str(ConditionType.USER_ROLE),
                         "operator": str(ConditionOperator.NOT_IN),
                         "value": [str(AuthLogUserRole.ADMIN_INTERNAL)]}],
            target=ConditionalAccessTarget.SOURCE_IP, priority=1)

        # The local DB admin gets in: pre-auth the role is admin-internal, taken from g.resolved_user (before_request
        # already looked the name up), so the NOT_IN condition does not match and the policy does not apply.
        res = self._auth(self.testadmin, self.testadminpw, remote_addr="10.0.0.5")
        self.assertEqual(200, res.status_code, res.json)
        self.assertTrue(res.json["result"]["value"]["token"], res.json)

        # A regular user from the same IP is not exempt and is denied.
        res = self._auth("cornelius", "test", remote_addr="10.0.0.5")
        self.assertEqual(401, res.status_code, res.json)
        self.assertEqual("MSG-DELTA", res.json["result"]["error"]["message"])
