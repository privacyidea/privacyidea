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
Tests for the conditional-access lockout policy templates: that the
catalog is listed correctly and that every template is a valid policy that
round-trips through ``create_lockout_policy`` (the create request a client
sends after prefilling from a template).
"""
from datetime import timedelta

from privacyidea.lib.conditional_access.authentication_event_types import (AuthEventType, AuthEventOutcome,
                                                                           outcome_of)
from privacyidea.lib.conditional_access.engine import (
    AccessDecision,
    LockoutAction,
    evaluate_access_decision,
    evaluate_lockout_policies,
    get_ip_block,
    get_user_lockout,
    is_ip_blocked,
    is_user_locked,
)
from privacyidea.lib.conditional_access.lockout_policy import create_lockout_policy, get_lockout_policy
from privacyidea.lib.conditional_access.lockout_policy_template import list_lockout_policy_templates
from privacyidea.lib.smtpserver import add_smtpserver, delete_smtpserver
from privacyidea.models import Admin, db
from privacyidea.models.lockout_policy import (
    LockoutPolicy,
    LockoutPolicyCounterType,
    LockoutPolicyStage,
    LockoutStageAction,
)
from privacyidea.models.utils import utc_now
from . import smtpmock
from .base import MyTestCase
from .conditional_access_lockout_base import LockoutTestCase

VALID_EVENT_TYPES = {event_type.value for event_type in AuthEventType}
VALID_ACTIONS = {action.value for action in LockoutAction}


class LockoutPolicyTemplateTestCase(MyTestCase):

    def tearDown(self):
        for model in (LockoutStageAction, LockoutPolicyStage, LockoutPolicyCounterType, LockoutPolicy):
            db.session.query(model).delete()
        db.session.commit()
        super().tearDown()

    def _policy(self, key):
        return next(entry["policy"] for entry in list_lockout_policy_templates() if entry["key"] == key)

    def test_catalog_lists_the_shipped_templates(self):
        catalog = {entry["key"]: entry for entry in list_lockout_policy_templates()}
        self.assertIn("password_bruteforce", catalog, "template missing from catalog")
        self.assertIn("mfa_bruteforce", catalog, "template missing from catalog")
        self.assertIn("password_spraying", catalog, "template missing from catalog")
        self.assertIn("user_enumeration", catalog, "template missing from catalog")
        self.assertIn("user_rate_limiting", catalog, "template missing from catalog")
        self.assertIn("user_failed_rate_limiting", catalog, "template missing from catalog")
        self.assertIn("ip_failed_rate_limiting", catalog, "template missing from catalog")
        self.assertIn("ip_rate_limiting", catalog, "template missing from catalog")
        # every entry carries a non-empty description and a policy dict
        for key, entry in catalog.items():
            self.assertTrue(entry["description"].strip(), f"{key}: empty description")
            self.assertIsInstance(entry["policy"], dict, f"{key}: policy not a dict")

    def test_every_template_is_a_valid_policy(self):
        # Each template must use only known event types and actions and must be
        # accepted by the real create path (fail-closed validation), so a broken
        # shipped template is caught here rather than at admin runtime.
        for entry in list_lockout_policy_templates():
            template = entry["policy"]
            self.assertTrue(set(template["counter_types_to_track"]) <= VALID_EVENT_TYPES, entry["key"])
            for stage in template["stages"]:
                for action in stage["actions"]:
                    self.assertIn(action["action_type"], VALID_ACTIONS,
                                  f"Invalid action type {action['action_type']} in lockout policy template "
                                  f"{entry['key']}")
            policy_id = create_lockout_policy(**{**template, "name": f"instance-{entry['key']}"})
            policy = get_lockout_policy(policy_id)
            self.assertListEqual(template["counter_types_to_track"], policy["counter_types_to_track"],
                                 f"{entry['key']}: counter types not preserved")
            self.assertEqual(len(template["stages"]), len(policy["stages"]),
                             f"{entry['key']}: stage count changed")

    def test_mfa_template_stage_shape(self):
        template = self._policy("mfa_bruteforce")
        # progressive: three ascending thresholds, most severe evaluated first
        thresholds = [stage["failure_threshold"] for stage in template["stages"]]
        self.assertListEqual([3, 5, 10], thresholds, "unexpected thresholds")
        self.assertListEqual(["MFA_FAIL"], template["counter_types_to_track"], "unexpected counter types")

    def test_list_returns_fresh_copies(self):
        # mutating a returned policy must not corrupt the shared catalog
        first = self._policy("password_bruteforce")
        first["name"] = "mutated"
        first["stages"].clear()
        second = self._policy("password_bruteforce")
        self.assertEqual("Password Brute-Force", second["name"], "catalog name was mutated")
        self.assertTrue(second["stages"], "catalog stages were mutated")

    def test_failed_rate_limit_failure_set_is_exhaustively_classified(self):
        # The failed-attempt rate-limit templates use explicit, curated failure lists (not a dynamic derivation), so a
        # new failure event type is never silently pulled into a throttle. This guard fails when a FAILURE-outcome
        # type is neither counted by the per-user failed template nor listed as deliberately excluded here (with the
        # reason), forcing whoever adds it to decide - add it to _USER_AUTH_FAILURES or exclude it here.
        user_excluded = {
            AuthEventType.NOT_AUTHORIZED,           # authorization denial, not an authentication failure
            AuthEventType.USER_UNKNOWN,             # inert for a user target; the per-IP set counts it (enumeration)
            AuthEventType.ENROLLMENT_CANCELED_FAIL,  # enrollment housekeeping, not a credential attempt
        }
        all_failures = {event_type.value for event_type in AuthEventType
                        if outcome_of(event_type) == AuthEventOutcome.FAILURE}
        user_counted = {str(t) for t in self._policy("user_failed_rate_limiting")["counter_types_to_track"]}
        ip_counted = {str(t) for t in self._policy("ip_failed_rate_limiting")["counter_types_to_track"]}
        excluded_values = {event_type.value for event_type in user_excluded}
        self.assertTrue(user_counted <= all_failures, "user failed rate-limit counts a non-failure event type")
        self.assertSetEqual(all_failures, user_counted | excluded_values,
                            "a new FAILURE event type must be added to _USER_AUTH_FAILURES or excluded in this test")
        self.assertSetEqual(set(), user_counted & excluded_values, "an event type is both counted and excluded")
        # The per-IP failed set is exactly the per-user set plus USER_UNKNOWN: distinct unknown usernames from one IP
        # are the enumeration signal, which a per-user target cannot see.
        self.assertSetEqual(user_counted | {AuthEventType.USER_UNKNOWN.value}, ip_counted,
                            "the IP failed rate-limit set must be the user set plus USER_UNKNOWN")

    def test_template_keys_are_unique(self):
        keys = [entry["key"] for entry in list_lockout_policy_templates()]
        self.assertEqual(len(keys), len(set(keys)), f"duplicate template key: {keys}")


class LockoutTemplateBehaviourTestCase(LockoutTestCase):
    """
    End-to-end behaviour of the shipped templates: create the real policy from a
    template (exactly as a client does after prefilling), replay authentication
    failures through :func:`evaluate_lockout_policies`, and assert the right
    action fires - including the edge cases where the policy must *not* apply
    (aged-out failures, a successful login in between, an untracked event type).
    """

    def _create(self, key, configure_email=False):
        """
        Instantiate the shipped template *key* as a real policy. With
        *configure_email* the blank ``smtp_identifier`` the template leaves for
        the admin is filled in, so the EMAIL_ADMIN actions actually send.
        """
        policy = next(entry["policy"] for entry in list_lockout_policy_templates()
                      if entry["key"] == key)
        if configure_email:
            for stage in policy["stages"]:
                for action in stage["actions"]:
                    if action["action_type"] in (LockoutAction.EMAIL_ADMIN, LockoutAction.EMAIL_USER):
                        action["action_value"]["smtp_identifier"] = "lockoutmail"
        return create_lockout_policy(**policy)

    # --- password brute-force template ----------------------------------------

    def test_password_bruteforce_locks_after_threshold(self):
        # The template tracks PASSWORD_FAIL and PIN_FAIL together: 6 + 4 = 10
        # reaches the threshold although neither type alone does.
        now = utc_now()
        self._create("password_bruteforce")
        self._seed_events(AuthEventType.PASSWORD_FAIL, 6, timestamp=now)
        self._seed_events(AuthEventType.PIN_FAIL, 4, timestamp=now)
        evaluate_lockout_policies(self.user, AuthEventType.PIN_FAIL, now=now)
        status = get_user_lockout(self.user, now=now)
        self.assertIsNotNone(status, "user not locked on combined count")
        self.assertFalse(status.permanent, "lock is permanent, expected timed")
        self.assertEqual(900, status.seconds_remaining, "wrong lock duration")

    def test_password_bruteforce_below_threshold_not_locked(self):
        now = utc_now()
        self._create("password_bruteforce")
        self._seed_events(AuthEventType.PASSWORD_FAIL, 9, timestamp=now)
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL, now=now)
        self.assertFalse(is_user_locked(self.user, now=now), "user locked below threshold")

    def test_password_bruteforce_failures_outside_window_not_counted(self):
        # Ten failures, but older than the 900s window -> aged out, no lock.
        now = utc_now()
        self._create("password_bruteforce")
        self._seed_events(AuthEventType.PASSWORD_FAIL, 10, timestamp=now - timedelta(seconds=1000))
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL, now=now)
        self.assertFalse(is_user_locked(self.user, now=now), "user locked on aged-out failures")

    # --- MFA brute-force template (progressive) -------------------------------

    def test_mfa_bruteforce_escalates_across_stages(self):
        # Replay an attacker whose MFA keeps failing: one policy escalates from a
        # short lock, to a longer lock, to a permanent lock as failures pile up.
        now = utc_now()
        self._create("mfa_bruteforce")

        self._seed_events(AuthEventType.MFA_FAIL, 3, timestamp=now)
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL, now=now)
        self.assertEqual(600, get_user_lockout(self.user, now=now).seconds_remaining,
                         "first stage: wrong lock duration")

        self._seed_events(AuthEventType.MFA_FAIL, 2, timestamp=now)  # total 5
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL, now=now)
        self.assertEqual(1800, get_user_lockout(self.user, now=now).seconds_remaining,
                         "second stage: did not escalate to 1800s")

        self._seed_events(AuthEventType.MFA_FAIL, 5, timestamp=now)  # total 10
        evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL, now=now)
        self.assertTrue(get_user_lockout(self.user, now=now).permanent,
                        "third stage: did not escalate to permanent lock")

    @smtpmock.activate
    def test_mfa_bruteforce_second_stage_locks_longer_and_emails_admin(self):
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        db.session.add(Admin(username="ca_soc", email="soc@example.com"))
        db.session.commit()
        try:
            now = utc_now()
            self._create("mfa_bruteforce", configure_email=True)
            self._seed_events(AuthEventType.MFA_FAIL, 5, timestamp=now)
            notices = evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL, now=now)
            status = get_user_lockout(self.user, now=now)
            self.assertFalse(status.permanent, "lock is permanent, expected timed")
            self.assertEqual(1800, status.seconds_remaining, "wrong lock duration")
            self.assertIn("soc@example.com", smtpmock.get_sent_recipient(), "admin not emailed")
            self.assertEqual(["Your administrator has been notified by email."], notices, "wrong login notice")
        finally:
            Admin.query.filter_by(username="ca_soc").delete()
            db.session.commit()
            delete_smtpserver("lockoutmail")

    @smtpmock.activate
    def test_mfa_bruteforce_third_stage_permanent_lock_and_emails_admin(self):
        smtpmock.setdata(response={})
        add_smtpserver(identifier="lockoutmail", server="1.2.3.4", tls=False)
        db.session.add(Admin(username="ca_soc", email="soc@example.com"))
        db.session.commit()
        try:
            now = utc_now()
            self._create("mfa_bruteforce", configure_email=True)
            self._seed_events(AuthEventType.MFA_FAIL, 10, timestamp=now)
            evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL, now=now)
            status = get_user_lockout(self.user, now=now)
            self.assertTrue(status.permanent, "lock not permanent")
            self.assertIsNone(status.seconds_remaining, "permanent lock has remaining time")
            self.assertIn("soc@example.com", smtpmock.get_sent_recipient(), "admin not emailed")
        finally:
            Admin.query.filter_by(username="ca_soc").delete()
            db.session.commit()
            delete_smtpserver("lockoutmail")

    def test_mfa_bruteforce_shipped_template_locks_without_smtp_configured(self):
        # The shipped template leaves smtp_identifier blank for the admin to fill
        # in. Until they do, the EMAIL_ADMIN action is a no-op (no login notice),
        # but the lock itself must still fire.
        now = utc_now()
        self._create("mfa_bruteforce")  # email deliberately left unconfigured
        self._seed_events(AuthEventType.MFA_FAIL, 5, timestamp=now)
        notices = evaluate_lockout_policies(self.user, AuthEventType.MFA_FAIL, now=now)
        self.assertEqual(1800, get_user_lockout(self.user, now=now).seconds_remaining,
                         "lock did not fire without SMTP configured")
        self.assertEqual([], notices, "unexpected login notice")

    # --- per-user rate limit (all attempts, DENY) -----------------------------

    def test_user_rate_limiting_denies_after_threshold_any_outcome(self):
        # Counts every attempt regardless of outcome: 10 successes + 5 failures + 5 abandoned = 20 attempts reach the
        # threshold, so the next request is denied pre-auth (DENY, never a lock).
        now = utc_now()
        self._create("user_rate_limiting")
        self._seed_attempts(AuthEventType.LOGIN_SUCCESS, 10, timestamp=now, start=0)
        self._seed_attempts(AuthEventType.MFA_FAIL, 5, timestamp=now, start=10)
        self._seed_attempts(AuthEventType.CHALLENGE_TRIGGERED, 5, timestamp=now, start=15)
        self.assertEqual(AccessDecision.DENY, evaluate_access_decision(self.user, now=now))
        self.assertFalse(is_user_locked(self.user, now=now), "a rate limit must not lock the account")

    def test_user_rate_limiting_below_threshold_continues(self):
        now = utc_now()
        self._create("user_rate_limiting")
        self._seed_attempts(AuthEventType.LOGIN_SUCCESS, 19, timestamp=now)
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(self.user, now=now))

    # --- per-user failed-attempt rate limit (DENY) ----------------------------

    def test_user_failed_rate_limiting_denies_after_failed_threshold(self):
        # 5 wrong passwords + 5 wrong challenge answers = 10 failed attempts reach the threshold.
        now = utc_now()
        self._create("user_failed_rate_limiting")
        self._seed_attempts(AuthEventType.PASSWORD_FAIL, 5, timestamp=now, start=0)
        self._seed_attempts(AuthEventType.CHALLENGE_ANSWERED_FAIL, 5, timestamp=now, start=5)
        self.assertEqual(AccessDecision.DENY, evaluate_access_decision(self.user, now=now))

    def test_user_failed_rate_limiting_ignores_successful_attempts(self):
        # Successful attempts reduce to LOGIN_SUCCESS (not a tracked failure type), so a busy successful client is
        # never throttled: 9 failures stay below the threshold no matter how many successful logins occur alongside.
        now = utc_now()
        self._create("user_failed_rate_limiting")
        self._seed_attempts(AuthEventType.MFA_FAIL, 9, timestamp=now, start=0)
        self._seed_attempts(AuthEventType.LOGIN_SUCCESS, 50, timestamp=now, start=9)
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(self.user, now=now))

    # --- per-IP failed-attempt rate limit (distinct accounts, DENY) -----------

    def test_ip_failed_rate_limiting_denies_after_distinct_failed_accounts(self):
        # Distinct accounts the IP failed against, real or probed: 10 wrong-password real users + 10 unknown-username
        # probes = 20 distinct accounts reach the threshold (enumeration folds into the failed fan-out signal).
        now = utc_now()
        ip = "203.0.113.40"
        self._create("ip_failed_rate_limiting")
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=10, timestamp=now)
        self._seed_ip_unknown_events(ip, AuthEventType.USER_UNKNOWN,
                                     [f"ghost{i}" for i in range(10)], timestamp=now)
        self.assertEqual(AccessDecision.DENY, evaluate_access_decision(self.user, source_ip=ip, now=now))

    def test_ip_failed_rate_limiting_below_threshold_continues(self):
        now = utc_now()
        ip = "203.0.113.41"
        self._create("ip_failed_rate_limiting")
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=19, timestamp=now)
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(self.user, source_ip=ip, now=now))

    # --- per-IP rate limit (all outcomes, distinct accounts) - ships dry-run ---

    def test_ip_rate_limiting_ships_dry_run_and_does_not_enforce(self):
        # This template counts successes too, so it ships dry_run=True: even well past the threshold it only logs the
        # would-be decision and enforces nothing (CONTINUE), so a legitimate shared-egress IP is never blocked.
        now = utc_now()
        ip = "203.0.113.42"
        policy_id = self._create("ip_rate_limiting")
        self.assertTrue(get_lockout_policy(policy_id)["dry_run"], "ip_rate_limiting must ship as dry-run")
        self._seed_ip_events(ip, AuthEventType.LOGIN_SUCCESS, n_users=35, timestamp=now)
        self.assertEqual(AccessDecision.CONTINUE, evaluate_access_decision(self.user, source_ip=ip, now=now))

    # --- user enumeration template (source_ip target) -------------------------

    def test_user_enumeration_blocks_ip_after_distinct_unknown_usernames(self):
        now = utc_now()
        ip = "203.0.113.30"
        self._create("user_enumeration")
        self._seed_ip_unknown_events(ip, AuthEventType.USER_UNKNOWN,
                                     [f"ghost{i}" for i in range(10)], timestamp=now)
        evaluate_lockout_policies(self.user, AuthEventType.USER_UNKNOWN, source_ip=ip, now=now)
        status = get_ip_block(ip, now=now)
        self.assertIsNotNone(status, "IP not blocked after distinct unknown usernames")
        self.assertFalse(status.permanent, "block is permanent, expected timed")
        self.assertEqual(3600, status.seconds_remaining, "wrong block duration")

    def test_user_enumeration_below_threshold_not_blocked(self):
        now = utc_now()
        ip = "203.0.113.31"
        self._create("user_enumeration")
        self._seed_ip_unknown_events(ip, AuthEventType.USER_UNKNOWN,
                                     [f"ghost{i}" for i in range(9)], timestamp=now)
        evaluate_lockout_policies(self.user, AuthEventType.USER_UNKNOWN, source_ip=ip, now=now)
        self.assertFalse(is_ip_blocked(ip, now=now), "IP blocked below the distinct-unknown-username threshold")

    def test_user_enumeration_repeated_unknown_username_is_one_distinct(self):
        # Many probes of the *same* nonexistent username are one distinct account, so they must not trip the block
        # (the signal is fan-out across accounts, not raw volume against one).
        now = utc_now()
        ip = "203.0.113.32"
        self._create("user_enumeration")
        self._seed_ip_unknown_events(ip, AuthEventType.USER_UNKNOWN, ["ghost"] * 30, timestamp=now)
        evaluate_lockout_policies(self.user, AuthEventType.USER_UNKNOWN, source_ip=ip, now=now)
        self.assertFalse(is_ip_blocked(ip, now=now), "IP blocked on repeated same-username volume")

    # --- password spraying template (source_ip target) ------------------------

    def test_password_spraying_below_threshold_not_blocked(self):
        now = utc_now()
        ip = "203.0.113.21"
        self._create("password_spraying")
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=19, timestamp=now)
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL, source_ip=ip, now=now)
        self.assertFalse(is_ip_blocked(ip, now=now), "IP blocked below the distinct-user threshold")

    def test_password_spraying_blocks_ip_after_distinct_users(self):
        # The template tracks PASSWORD_FAIL and PIN_FAIL together: 12 + 8 = 20
        # distinct users reach the threshold although neither type alone does.
        now = utc_now()
        ip = "203.0.113.22"
        self._create("password_spraying")
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=12, timestamp=now)
        self._seed_ip_events(ip, AuthEventType.PIN_FAIL, n_users=8, timestamp=now, start=12)
        evaluate_lockout_policies(self.user, AuthEventType.PIN_FAIL, source_ip=ip, now=now)
        status = get_ip_block(ip, now=now)
        self.assertIsNotNone(status, "IP not blocked on combined distinct-user count")
        self.assertFalse(status.permanent, "block is permanent, expected timed")
        self.assertEqual(3600, status.seconds_remaining, "wrong block duration")

    def test_password_spraying_counts_distinct_users_not_events(self):
        # Many failures from only a few users must not trip the per-IP detection:
        # 5 users x 10 failures = 50 rows but only 5 distinct users (< 20).
        now = utc_now()
        ip = "203.0.113.23"
        self._create("password_spraying")
        self._seed_ip_events(ip, AuthEventType.PASSWORD_FAIL, n_users=5, per_user=10, timestamp=now)
        evaluate_lockout_policies(self.user, AuthEventType.PASSWORD_FAIL, source_ip=ip, now=now)
        self.assertFalse(is_ip_blocked(ip, now=now), "IP blocked on event count instead of distinct users")
