"""
This test file tests the lib.tokens.questionnairetoken
This depends on lib.tokenclass
"""

import json

from privacyidea.lib.config import set_privacyidea_config
from privacyidea.lib.token import init_token, import_tokens, get_tokens
from privacyidea.lib.tokens.questionnairetoken import QuestionnaireTokenClass
from privacyidea.models import Token
from .base import MyTestCase


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

    def test_07_questionnaire_token_export(self):
        # Set up the QuestionnaireTokenClass for testing
        set_privacyidea_config("question.num_answers", 3)
        token = init_token({"type": "question",
                            "pin": self.pin,
                            "serial": self.serial1,
                            "user": "cornelius",
                            "realm": self.realm1,
                            "questions": self.j_questions,
                            "description": "this is a questionnaire token export test"
                            })

        # Test that all expected keys are present in the exported dictionary
        exported_data = token.export_token()
        expected_keys = ["serial", "type", "description", "issuer"]
        self.assertTrue(set(expected_keys).issubset(exported_data.keys()))

        expected_tokeninfo_keys = ["tokenkind", "frage1", "frage2", "frage3"]
        self.assertTrue(set(expected_tokeninfo_keys).issubset(exported_data["info_list"].keys()))

        # Test that the exported values match the token's data
        self.assertEqual(exported_data["serial"], "QUST1234")
        self.assertEqual(exported_data["type"], "question")
        self.assertEqual(exported_data["description"], "this is a questionnaire token export test")
        self.assertEqual(exported_data["info_list"]["tokenkind"], "software")
        self.assertEqual(exported_data["issuer"], "privacyIDEA")
        self.assertEqual(exported_data["info_list"]["frage1"], "antwort1")
        self.assertEqual(exported_data["info_list"]["frage2"], "antwort2")
        self.assertEqual(exported_data["info_list"]["frage3"], "antwort3")

        # Clean up
        token.delete_token()

    def test_08_questionnaire_token_import(self):
        # Define the token data to be imported
        token_data = [{'description': 'this is a questionnaire token export test',
                       'issuer': 'privacyIDEA',
                       'serial': 'QUST1234',
                       'type': 'question',
                       'info_list': {'frage1': 'antwort1',
                                     'frage1.type': 'password',
                                     'frage2': 'antwort2',
                                     'frage2.type': 'password',
                                     'frage3': 'antwort3',
                                     'frage3.type': 'password',
                                     'tokenkind': 'software'}
                       }]

        # Import the token
        import_tokens(token_data)

        # Retrieve the imported token
        token = get_tokens(serial=token_data[0]["serial"])[0]

        # Verify that the token data matches the imported data
        self.assertEqual(token.token.serial, token_data[0]["serial"])
        self.assertEqual(token.type, token_data[0]["type"])
        self.assertEqual(token.token.description, token_data[0]["description"])
        self.assertEqual(token.get_tokeninfo("frage1"), 'antwort1')
        self.assertEqual(token.get_tokeninfo("frage2"), 'antwort2')

        # cheak that the token can be used
        r = token.create_challenge()
        question = r[1]
        transactionid = r[2]
        r = token.check_challenge_response(passw=self.questions[question],
                                           options={"transaction_id":
                                                        transactionid})
        self.assertEqual(r, 1)

        # Clean up
        token.delete_token()
