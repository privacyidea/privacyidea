"""
A single-use object is used by one request only, also when two requests arrive at the same time: a challenge, an
answered push approval, a FIDO2 challenge, a container registration challenge, a recovery code, and the last step
of a multi-step challenge.

Each test makes both requests wait at a barrier after they have read and verified the object and before either
removes it. This is the interleaving two application workers produce when two requests for the same token or
transaction arrive within a few milliseconds.

Needs a database with row locks; on SQLite the lock serializes the writers, so the tests skip there.
"""
import json
import threading
import time
from datetime import datetime, timezone
from functools import partial
from unittest import mock

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

import privacyidea.lib.containerclass as containerclass_module
import privacyidea.lib.passwordreset as passwordreset_module
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.config import set_privacyidea_config
from privacyidea.lib.container import init_container, find_container_by_serial, delete_container_by_serial
from privacyidea.lib.crypto import hash_with_pepper
from privacyidea.lib.fido2.challenge import verify_fido2_challenge
from privacyidea.lib.fido2.policy_action import FIDO2PolicyAction
from privacyidea.lib.passwordreset import check_recoverycode
from privacyidea.lib.policy import SCOPE, set_policy, delete_policy
from privacyidea.lib.token import create_challenge, get_one_token, init_token, remove_token
from privacyidea.lib.tokenclass import AUTH_DATE_FORMAT, TokenClass
from privacyidea.lib.tokens.HMAC import HmacOtp
from privacyidea.lib.tokens.hotptoken import HotpTokenClass
from privacyidea.lib.tokens.pushtoken import PushAction, POLL_ONLY, PushTokenClass
from privacyidea.lib.tokens.questionnairetoken import QuestionnaireTokenClass
from privacyidea.lib.user import User
from privacyidea.models import db, PasswordReset
from tests.base import MyApiTestCase
from tests.test_api_push_validate import PushTokenTestMixin, REGISTRATION_URL

QUESTIONS = {"frage1": "antwort1", "frage2": "antwort2", "frage3": "antwort3"}
QUESTION_PIN = "pin"
# RFC 4226 test key and its first OTP value
OTP_KEY = "3132333435363738393031323334353637383930"
HOTP_AT_COUNTER_0 = "755224"


def run_in_parallel(app, functions: list) -> list:
    """Run each function in its own thread and app context; return its result, or "exception: ..." if it raised."""
    results = [None] * len(functions)

    def run(index: int) -> None:
        with app.app_context():
            try:
                results[index] = functions[index]()
            except Exception as exception:  # every thread reports back
                results[index] = f"exception: {exception!r}"[:200]
            finally:
                db.session.remove()

    threads = [threading.Thread(target=run, args=(index,)) for index in range(len(functions))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    # End this thread's transaction, so the assertions read what the requests committed (MariaDB/MySQL
    # REPEATABLE READ would otherwise keep showing an older snapshot).
    db.session.rollback()
    return results


def synchronize_after(target, attribute: str, parties: int):
    """Patch target.attribute so that each thread waits at a barrier once, right after the original returned.

    A thread that arrives alone is not held up: the barrier times out and the requests run one after the other,
    which is the outcome the tests expect from an implementation that serializes them itself.
    """
    original = getattr(target, attribute)
    barrier = threading.Barrier(parties, timeout=5)
    thread_state = threading.local()

    def wrapper(*args, **kwargs):
        result = original(*args, **kwargs)
        if not getattr(thread_state, "synchronized", False):
            thread_state.synchronized = True
            try:
                barrier.wait()
            except threading.BrokenBarrierError:
                pass
        return result

    return mock.patch.object(target, attribute, wrapper)


def results_of(responses: list) -> list:
    """The result of each response body, or the exception string of a thread that did not get one."""
    return [body["result"] if isinstance(body, dict) else body for body in responses]


def accepted(results: list) -> int:
    return sum(1 for result in results if isinstance(result, dict) and result.get("value") is True)


def seed_auth_counters(token: TokenClass) -> TokenClass:
    """Write the auth counters and last_auth, so parallel requests update those rows instead of racing to insert
    them - one of them would die on the tiix_2 unique key and hide the behavior under test."""
    token.set_count_auth(0)
    token.set_count_auth_success(0)
    token.write_tokeninfo("last_auth", datetime.now(timezone.utc).strftime(AUTH_DATE_FORMAT))
    token.save()
    return token


class ParallelRequestTestCase(MyApiTestCase):
    """The interleaving these tests force needs a database that takes row locks."""

    def setUp(self):
        super().setUp()
        if db.engine.dialect.name == "sqlite":
            self.skipTest("SQLite serializes the writers, the interleaving cannot be reproduced")


class ParallelChallengeConsumeTestCase(PushTokenTestMixin, ParallelRequestTestCase):

    def test_recovery_code_is_accepted_once(self):
        self.setUp_user_realms()
        user = User("cornelius", self.realm1)
        # The recovery code is bound to the user store it was issued for, so it carries the resolver.
        PasswordReset(hash_with_pepper("recovery-code-1"), username=user.login, realm=user.realm,
                      resolver=user.resolver).save()

        redeem = partial(check_recoverycode, User("cornelius", self.realm1), "recovery-code-1")
        with synchronize_after(passwordreset_module, "verify_with_pepper", 2):
            results = run_in_parallel(self.app, [redeem, redeem])

        self.assertEqual(1, results.count(True), results)

    def test_answered_push_challenge_logs_in_once(self):
        self.setUp_user_realms()
        set_policy("push_config", scope=SCOPE.ENROLL,
                   action=f"{PushAction.FIREBASE_CONFIG}={POLL_ONLY},{PushAction.REGISTRATION_URL}={REGISTRATION_URL}")
        self._enroll_push_token()
        seed_auth_counters(get_one_token(serial=self.serial_push))

        def answered_push_challenge() -> str:
            with self.app.test_request_context('/validate/check', method='POST',
                                               data={"user": "selfservice", "pass": "push_pin"}):
                transaction_id = self.app.full_dispatch_request().json["detail"]["transaction_id"]
            challenge = get_challenges(serial=self.serial_push, transaction_id=transaction_id)[0]
            # What the smartphone's signed confirmation does in /ttype/push
            challenge.set_otp_status(True)
            challenge.save()
            return transaction_id

        # One sequential login first, so the per-user attributes a login stores already exist
        with self.app.test_request_context('/validate/check', method='POST',
                                           data={"user": "selfservice", "pass": "",
                                                 "transaction_id": answered_push_challenge()}):
            self.assertTrue(self.app.full_dispatch_request().json["result"]["value"])
        transaction_id = answered_push_challenge()

        def finalize():
            with self.app.test_client() as client:
                response = client.post("/validate/check", data={"user": "selfservice", "pass": "",
                                                                "transaction_id": transaction_id})
                return response.json["result"].get("value")

        try:
            with synchronize_after(PushTokenClass, "_scan_challenge_response", 2):
                results = run_in_parallel(self.app, [finalize, finalize])
            self.assertEqual(1, results.count(True), results)
        finally:
            remove_token(self.serial_push)
            delete_policy("push_config")

    def test_fido2_challenge_is_used_once(self):
        # A HOTP token stands in for the passkey; its check_otp reports a verified assertion. What is tested is
        # that the challenge of the transaction is used once, not the cryptographic check.
        seed_auth_counters(init_token({"type": "hotp", "otpkey": self.otpkey, "serial": "FIDOSTUB"}))
        challenge = create_challenge(serial="", challenge="nonce", validitytime=120,
                                     data={FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT: "preferred"})
        transaction_id = challenge.transaction_id
        params = {"authenticatorData": "a", "clientDataJSON": "c", "signature": "s", "HTTP_ORIGIN": "https://pi"}
        barrier = threading.Barrier(2, timeout=5)

        def verified_assertion(*args, **kwargs) -> int:
            try:
                barrier.wait()
            except threading.BrokenBarrierError:
                pass
            return 1

        def verify() -> bool:
            return verify_fido2_challenge(transaction_id, get_one_token(serial="FIDOSTUB"), dict(params)).success > 0

        try:
            with mock.patch.object(HotpTokenClass, "check_otp", side_effect=verified_assertion):
                results = run_in_parallel(self.app, [verify, verify])
            self.assertEqual(1, results.count(True), results)
        finally:
            remove_token("FIDOSTUB")

    def test_container_registration_challenge_is_used_once(self):
        container_serial = init_container({"type": "smartphone"})["container_serial"]
        container = find_container_by_serial(container_serial)
        scope = "https://pi.net/container/register/finalize"
        challenge_data = container.create_challenge(scope=scope)
        message = f"{challenge_data['nonce']}|{challenge_data['time_stamp']}|{container_serial}|{scope}"

        def finalize() -> bool:
            private_key = ec.generate_private_key(ec.SECP384R1())
            signature = private_key.sign(message.encode("utf-8"), ec.ECDSA(hashes.SHA256()))
            return find_container_by_serial(container_serial).validate_challenge(
                signature, private_key.public_key(), scope, transaction_id=challenge_data["transaction_id"])

        try:
            with synchronize_after(containerclass_module, "verify_ecc", 2):
                results = run_in_parallel(self.app, [finalize, finalize])
            self.assertEqual(1, results.count(True), results)
        finally:
            delete_container_by_serial(container_serial)


class ParallelMultiStepChallengeTestCase(ParallelRequestTestCase):
    """
    The multi-step token types (questionnaire, indexed secret, 4eyes) keep the answered challenge until
    has_further_challenge has read it, so check_token_list consumes it for them.
    """

    def setUp(self):
        super().setUp()
        set_privacyidea_config("question.num_answers", 3)

    def _create_token(self, serial: str) -> TokenClass:
        return seed_auth_counters(init_token({"type": "question", "serial": serial, "pin": QUESTION_PIN,
                                              "questions": json.dumps(QUESTIONS)}))

    def _trigger(self, serial: str) -> tuple[str, str]:
        """Ask for the first question and return its transaction id and the answer."""
        with self.app.test_client() as client:
            detail = client.post("/validate/check", data={"serial": serial, "pass": QUESTION_PIN}).json["detail"]
        return detail["transaction_id"], QUESTIONS[detail["message"]]

    def _answer(self, serial: str, transaction_id: str, answer: str) -> dict:
        """Answer one question and return the whole response body."""
        with self.app.test_client() as client:
            return client.post("/validate/check", data={"serial": serial, "transaction_id": transaction_id,
                                                        "pass": answer}).json

    def test_single_question_is_answered_once(self):
        serial = "PARQUST1"
        self._create_token(serial)
        transaction_id, answer = self._trigger(serial)

        answer_again = partial(self._answer, serial, transaction_id, answer)
        try:
            with synchronize_after(QuestionnaireTokenClass, "check_answer", 2):
                outcomes = results_of(run_in_parallel(self.app, [answer_again, answer_again]))
            self.assertEqual(1, accepted(outcomes), outcomes)
        finally:
            remove_token(serial)

    def test_last_question_of_a_multi_step_flow_is_answered_once(self):
        serial = "PARQUST2"
        set_policy("parallel_questions", scope=SCOPE.AUTH, action="question_number=2")
        self._create_token(serial)
        try:
            transaction_id, answer = self._trigger(serial)
            # The first step continues the flow with a second question under a new transaction id.
            first = self._answer(serial, transaction_id, answer)
            self.assertFalse(first["result"]["value"], first)
            last_transaction_id = first["detail"]["transaction_id"]
            self.assertNotEqual(transaction_id, last_transaction_id, first)
            last_answer = QUESTIONS[first["detail"]["message"]]

            answer_last = partial(self._answer, serial, last_transaction_id, last_answer)
            with synchronize_after(QuestionnaireTokenClass, "check_answer", 2):
                outcomes = results_of(run_in_parallel(self.app, [answer_last, answer_last]))

            self.assertEqual(1, accepted(outcomes), outcomes)
        finally:
            delete_policy("parallel_questions")
            remove_token(serial)

    def test_intermediate_step_hands_out_one_follow_up(self):
        """One answer buys one follow-up challenge, not one per request."""
        serial = "PARQUST3"
        set_policy("parallel_questions", scope=SCOPE.AUTH, action="question_number=2")
        self._create_token(serial)
        try:
            transaction_id, answer = self._trigger(serial)

            answer_first = partial(self._answer, serial, transaction_id, answer)
            with synchronize_after(QuestionnaireTokenClass, "check_answer", 2):
                responses = run_in_parallel(self.app, [answer_first, answer_first])

            follow_ups = [body["detail"].get("transaction_id") for body in responses if isinstance(body, dict)
                          if body["detail"].get("transaction_id")]
            self.assertEqual(1, len(follow_ups), responses)
        finally:
            delete_policy("parallel_questions")
            remove_token(serial)


class ParallelOtpCounterTestCase(ParallelRequestTestCase):
    """
    The OTP counter and the failcounter are advanced with a single conditional statement, so an OTP value is
    accepted once and every failed attempt is counted.
    """

    def _check(self, data: dict) -> dict:
        with self.app.test_client() as client:
            return client.post("/validate/check", data=data).json

    def _create_token(self, params: dict) -> TokenClass:
        return seed_auth_counters(init_token(params))

    def test_same_hotp_value_is_accepted_once(self):
        serial = "PARHOTP"
        token = self._create_token({"serial": serial, "type": "hotp", "otpkey": OTP_KEY, "pin": "pin"})
        self.assertEqual(0, token.token.count)
        send = partial(self._check, {"serial": serial, "pass": "pin" + HOTP_AT_COUNTER_0})

        try:
            with synchronize_after(HmacOtp, "checkOtp", 2):
                results = results_of(run_in_parallel(self.app, [send, send]))

            self.assertEqual(1, accepted(results), results)
            self.assertEqual(1, get_one_token(serial=serial).token.count)
        finally:
            remove_token(serial)

    def test_same_totp_value_is_accepted_once(self):
        serial = "PARTOTP"
        self._create_token({"serial": serial, "type": "totp", "otpkey": OTP_KEY, "pin": "pin", "timeStep": "30"})
        # Stay clear of a time step boundary, so both requests see the same step.
        if int(time.time()) % 30 > 25:
            time.sleep(6)
        totp_value = HmacOtp(digits=6).generate(key=bytes.fromhex(OTP_KEY), counter=int(time.time() // 30))
        send = partial(self._check, {"serial": serial, "pass": "pin" + totp_value})

        try:
            with synchronize_after(HmacOtp, "checkOtp", 2):
                results = results_of(run_in_parallel(self.app, [send, send]))

            self.assertEqual(1, accepted(results), results)
        finally:
            remove_token(serial)

    def test_every_parallel_wrong_value_counts(self):
        serial = "PARFAIL"
        parallel_requests = 5
        token = self._create_token({"serial": serial, "type": "hotp", "otpkey": OTP_KEY, "pin": "pin"})
        token.set_maxfail(10)
        token.save()
        sends = [partial(self._check, {"serial": serial, "pass": f"pin00000{index}"})
                 for index in range(parallel_requests)]

        try:
            with synchronize_after(HmacOtp, "checkOtp", parallel_requests):
                results = results_of(run_in_parallel(self.app, sends))

            self.assertEqual(0, accepted(results), results)
            self.assertEqual(parallel_requests, get_one_token(serial=serial).token.failcount)
        finally:
            remove_token(serial)
