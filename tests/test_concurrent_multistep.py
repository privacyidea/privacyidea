"""
The multi-step token types (questionnaire, indexed secret, 4eyes) keep the answered challenge until
has_further_challenge has read it, so check_token_list consumes it for them. Only one of several simultaneous
answers to the last step is accepted.

Every thread answers the question and then waits at a barrier, so all requests have read and verified the
challenge before any of them removes it. This is the interleaving two application workers produce when two
requests for the same transaction arrive within a few milliseconds.

Needs a database with row locks; on SQLite the lock serializes the writers, so the tests skip there.
"""
import json
import threading
from datetime import datetime, timezone
from functools import partial
from unittest import mock

from privacyidea.lib.config import set_privacyidea_config
from privacyidea.lib.policy import SCOPE, set_policy, delete_policy
from privacyidea.lib.token import init_token, remove_token
from privacyidea.lib.tokenclass import AUTH_DATE_FORMAT, TokenClass
from privacyidea.lib.tokens.questionnairetoken import QuestionnaireTokenClass
from privacyidea.models import db
from tests.base import MyApiTestCase

QUESTIONS = {"frage1": "antwort1", "frage2": "antwort2", "frage3": "antwort3"}
PIN = "pin"


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


def seed_auth_counters(token: TokenClass) -> TokenClass:
    """Write the auth counters and last_auth, so parallel requests update those rows instead of racing to insert
    them - one of them would die on the tiix_2 unique key and hide the behavior under test."""
    token.set_count_auth(0)
    token.set_count_auth_success(0)
    token.write_tokeninfo("last_auth", datetime.now(timezone.utc).strftime(AUTH_DATE_FORMAT))
    token.save()
    return token


class ParallelMultiStepChallengeTestCase(MyApiTestCase):

    def setUp(self):
        if db.engine.dialect.name == "sqlite":
            self.skipTest("SQLite serializes the writers, the interleaving cannot be reproduced")
        set_privacyidea_config("question.num_answers", 3)

    def _create_token(self, serial: str) -> TokenClass:
        return seed_auth_counters(init_token({"type": "question", "serial": serial, "pin": PIN,
                                              "questions": json.dumps(QUESTIONS)}))

    def _trigger(self, serial: str) -> tuple[str, str]:
        """Ask for the first question and return its transaction id and the answer."""
        with self.app.test_client() as client:
            detail = client.post("/validate/check", data={"serial": serial, "pass": PIN}).json["detail"]
        return detail["transaction_id"], QUESTIONS[detail["message"]]

    def _answer(self, serial: str, transaction_id: str, answer: str) -> dict:
        """Answer one question and return the whole response body."""
        with self.app.test_client() as client:
            return client.post("/validate/check", data={"serial": serial, "transaction_id": transaction_id,
                                                        "pass": answer}).json

    def _outcomes(self, responses: list) -> list:
        """The result of each response, or the exception string of a thread that did not get one."""
        return [body["result"] if isinstance(body, dict) else body for body in responses]

    @staticmethod
    def _accepted(outcomes: list) -> int:
        return sum(1 for outcome in outcomes if isinstance(outcome, dict) and outcome.get("value") is True)

    def test_01_single_question_is_answered_once(self):
        serial = "PARQUST1"
        self._create_token(serial)
        transaction_id, answer = self._trigger(serial)

        answer_again = partial(self._answer, serial, transaction_id, answer)
        with synchronize_after(QuestionnaireTokenClass, "check_answer", 2):
            outcomes = self._outcomes(run_in_parallel(self.app, [answer_again, answer_again]))

        remove_token(serial)
        self.assertEqual(1, self._accepted(outcomes), outcomes)

    def test_02_last_question_of_a_multi_step_flow_is_answered_once(self):
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
                outcomes = self._outcomes(run_in_parallel(self.app, [answer_last, answer_last]))

            self.assertEqual(1, self._accepted(outcomes), outcomes)
        finally:
            delete_policy("parallel_questions")
            remove_token(serial)
