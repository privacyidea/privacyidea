"""
This test file tests the lib.tokens.questionnairetoken
This depends on lib.tokenclass
"""

from .base import MyTestCase
from privacyidea.lib.tokens.questionnairetoken import QuestionnaireTokenClass
from privacyidea.lib.token import init_token
from privacyidea.lib.config import set_privacyidea_config
from privacyidea.models import Token
import json


class QuestionnaireTokenTestCase(MyTestCase):
    serial1 = "QUST1234"
    pin = "test"
    questions = {"frage1": "antwort1",
                 "frage2": "antwort2",
                 "frage3": "antwort3"
                 }
    j_questions = json.dumps(questions)

    dumb_questions = {"dumb questiontype": "answer"}
    j_dumb_questions = json.dumps(dumb_questions)
    # add_user, get_user, reset, set_user_identifiers

    def test_00_users(self):
        self.setUp_user_realms()

    def test_01_create_token(self):
        set_privacyidea_config("question.num_answers", 3)
        token = init_token({"type": "question",
                            "pin": self.pin,
                            "serial": self.serial1,
                            "user": "cornelius",
                            "realm": self.realm1,
                            "questions": self.j_questions
                            })
        self.assertEqual(token.type, "question")

        prefix = QuestionnaireTokenClass.get_class_prefix()
        self.assertEqual(prefix, "QUST")

        info = QuestionnaireTokenClass.get_class_info()
        self.assertEqual(info.get("type"), "question")

        info = QuestionnaireTokenClass.get_class_info("type")
        self.assertEqual(info, "question")

    def test_02_check_challenge(self):
        # Check the challenge request
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = QuestionnaireTokenClass(db_token)
        r = token.is_challenge_request(self.pin)
        self.assertEqual(r, True)
        r = token.is_challenge_request(self.pin + "123456")
        self.assertEqual(r, False)

        # Check create_challenge.
        # The challenge is a randomly selected question.
        r = token.create_challenge()
        self.assertEqual(r[0], True)
        question = r[1]
        transactionid = r[2]
        self.assertTrue(question in self.questions)

        # Now that we have the question, we can give the answer
        r = token.check_challenge_response(passw=self.questions[question],
                                           options={"transaction_id":
                                                        transactionid})
        self.assertEqual(r, 1)
        token.delete_token()

    def test_03_get_setting_type(self):
        r = QuestionnaireTokenClass.get_setting_type("question.question.1")
        self.assertEqual(r, "public")

    def test_04_dumb_question(self):
        set_privacyidea_config("question.num_answers", 1)
        token = init_token({"type": "question",
                            "pin": self.pin,
                            "serial": "2ndtoken",
                            "user": "cornelius",
                            "realm": self.realm1,
                            "questions": self.j_dumb_questions
                            })
        _r, question, _transaction, _none = token.create_challenge()
        self.assertEqual("dumb questiontype", question)
        token.delete_token()

    def test_05_unicode_question(self):
        questions = {'cité': 'Nîmes',
                     '城市': '北京',
                     'ciudad': 'Almería'}
        set_privacyidea_config("question.num_answers", 2)
        token = init_token({"type": "question",
                            "pin": self.pin,
                            "user": "cornelius",
                            "realm": self.realm1,
                            "questions": json.dumps(questions)
                            })
        self.assertEqual(token.type, "question")
        r = token.create_challenge()
        self.assertEqual(r[0], True)
        question = r[1]
        transactionid = r[2]
        self.assertTrue(question in questions)

        # Now that we have the question, we can give the answer
        r = token.check_challenge_response(passw=questions[question],
                                           options={"transaction_id": transactionid})
        self.assertEqual(r, 1)
        token.delete_token()

    def test_06_wrong_answer(self):
        questions = {'ciudad': 'Almería'}
        set_privacyidea_config("question.num_answers", 1)
        token = init_token({"type": "question",
                            "pin": self.pin,
                            "user": "cornelius",
                            "realm": self.realm1,
                            "questions": json.dumps(questions)
                            })
        self.assertEqual(token.type, "question")
        r = token.create_challenge()
        self.assertEqual(r[0], True)
        question = r[1]
        transactionid = r[2]
        self.assertTrue(question in questions)

        # What happens if the answer is wrong?
        r = token.check_challenge_response(passw='Málaga',
                                           options={"transaction_id": transactionid})
        self.assertEqual(r, -1)
        # Try to answer again
        r = token.check_challenge_response(passw='Almería',
                                           options={"transaction_id": transactionid})
        self.assertEqual(r, 1)
        token.delete_token()
