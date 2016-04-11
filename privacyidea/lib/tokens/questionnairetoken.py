# -*- coding: utf-8 -*-
#
#  http://www.privacyidea.org
#  2015-12-16 Initial writeup.
#             Cornelius Kölbel <cornelius@privacyidea.org>
#
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
__doc__ = """The questionnaire token is a challenge response token.
The user can define a set of answers to questions. Within the challenge the
user is asked one of these questions and can respond with the corresponding
answer.
"""

from privacyidea.api.lib.utils import getParam
from privacyidea.lib.config import get_from_config
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.log import log_with
from privacyidea.lib.error import TokenAdminError
import logging
from privacyidea.models import Challenge
from privacyidea.lib.challenge import get_challenges
import gettext
from privacyidea.lib.decorators import check_token_locked
import random
import json
_ = gettext.gettext

log = logging.getLogger(__name__)
optional = True
required = False
DEFAULT_NUM_ANSWERS = 5


class QuestionnaireTokenClass(TokenClass):

    """
    This is a Questionnaire Token. The token stores a list of questions and
    answers in the tokeninfo database table. The answers are encrypted.
    During authentication a random answer is selected and presented as
    challenge.
    The user has to remember and pass the right answer.
    """

    @staticmethod
    def get_class_type():
        """
        Returns the internal token type identifier
        :return: qust
        :rtype: basestring
        """
        return "question"

    @staticmethod
    def get_class_prefix():
        """
        Return the prefix, that is used as a prefix for the serial numbers.
        :return: QUST
        :rtype: basestring
        """
        return "QUST"

    @classmethod
    @log_with(log)
    def get_class_info(cls, key=None, ret='all'):
        """
        returns a subtree of the token definition

        :param key: subsection identifier
        :type key: string
        :param ret: default return value, if nothing is found
        :type ret: user defined
        :return: subsection if key exists or user defined
        :rtype: dict or scalar
        """
        res = {'type': cls.get_class_type(),
               'title': 'Questionnaire Token',
               'description': _('Questionnaire: Enroll Questions for the '
                                'user.'),
               'init': {},
               'config': {},
               'user':  ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {},
               }

        if key is not None and key in res:
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res
        return ret

    @log_with(log)
    def __init__(self, db_token):
        """
        Create a new QUST Token object from a database token

        :param db_token: instance of the orm db object
        :type db_token: DB object
        """
        TokenClass.__init__(self, db_token)
        self.set_type(self.get_class_type())
        self.hKeyRequired = False

    def update(self, param):
        """
        This method is called during the initialization process.

        :param param: parameters from the token init
        :type param: dict
        :return: None
        """
        j_questions = getParam(param, "questions", required)
        try:
            # If we have a string, we load the json format
            questions = json.loads(j_questions)
        except TypeError:
            # Obviously we have a dict...
            questions = j_questions
        num_answers = get_from_config("question.num_answers",
                                      DEFAULT_NUM_ANSWERS)
        if len(questions) < int(num_answers):
            raise TokenAdminError(_("You need to provide at least %s "
                                    "answers.") % num_answers)
        # Save all questions and answers and encrypt them
        for question, answer in questions.iteritems():
            self.add_tokeninfo(question, answer, value_type="password")
        TokenClass.update(self, param)

    def is_challenge_request(self, passw, user=None, options=None):
        """
        The questionnaire token is always a challenge response token.
        The challenge is triggered by providing the PIN as the password.

        :param passw: password, which might be pin or pin+otp
        :type passw: string
        :param user: The user from the authentication request
        :type user: User object
        :param options: dictionary of additional request parameters
        :type options: dict

        :return: true or false
        :rtype: bool
        """
        request_is_challenge = False
        options = options or {}
        pin_match = self.check_pin(passw, user=user, options=options)
        return pin_match

    def create_challenge(self, transactionid=None, options=None):
        """
        This method creates a challenge, which is submitted to the user.
        The submitted challenge will be preserved in the challenge
        database.

        The challenge is a randomly selected question of the available
        questions for this token.

        If no transaction id is given, the system will create a transaction
        id and return it, so that the response can refer to this transaction.

        :param transactionid: the id of this challenge
        :param options: the request context parameters / data
        :type options: dict
        :return: tuple of (bool, message, transactionid, attributes)
        :rtype: tuple

        The return tuple builds up like this:
        ``bool`` if submit was successful;
        ``message`` which is displayed in the JSON response;
        additional ``attributes``, which are displayed in the JSON response.
        """
        options = options or {}

        # Get a random question
        questions = []
        tinfo = self.get_tokeninfo()
        for question, answer in tinfo.iteritems():
            if question.endswith(".type") and answer == "password":
                # This is "Question1?.type" of type "password"
                # So this is actually a question and we add the question to
                # the list
                questions.append(question.strip(".type"))
        message = random.choice(questions)
        attributes = None

        validity = int(get_from_config('DefaultChallengeValidityTime', 120))
        tokentype = self.get_tokentype().lower()
        # Maybe there is a QUESTIONChallengeValidityTime...
        lookup_for = tokentype.capitalize() + 'ChallengeValidityTime'
        validity = int(get_from_config(lookup_for, validity))

        # Create the challenge in the database
        db_challenge = Challenge(self.token.serial,
                                 transaction_id=transactionid,
                                 challenge=message,
                                 validitytime=validity)
        db_challenge.save()
        self.challenge_janitor()
        return True, message, db_challenge.transaction_id, attributes

    def check_answer(self, given_answer, challenge_object):
        """
        Check if the given answer is the answer to the sent question.
        The question for this challenge response was stored in the
        challenge_object.

        Then we get the answer from the tokeninfo.

        :param given_answer: The answer given by the user
        :param challenge_object: The challenge object as stored in the database
        :return: in case of success: 1
        """
        res = -1
        question = challenge_object.challenge
        answer = self.get_tokeninfo(question)
        if answer == given_answer:
            res = 1
        else:
            log.debug("The answer for token {0!s} does not match.".format(
                      self.get_serial()))
        return res

    @check_token_locked
    def check_challenge_response(self, user=None, passw=None, options=None):
        """
        This method verifies if there is a matching question for the given
        passw and also verifies if the answer is correct.

        It then returns the the otp_counter = 1

        :param user: the requesting user
        :type user: User object
        :param passw: the password - in fact it is the answer to the question
        :type passw: string
        :param options: additional arguments from the request, which could
                        be token specific. Usually "transaction_id"
        :type options: dict
        :return: return otp_counter. If -1, challenge does not match
        :rtype: int
        """
        options = options or {}
        otp_counter = -1

        # fetch the transaction_id
        transaction_id = options.get('transaction_id')
        if transaction_id is None:
            transaction_id = options.get('state')

        # get the challenges for this transaction ID
        if transaction_id is not None:
            challengeobject_list = get_challenges(serial=self.token.serial,
                                                  transaction_id=transaction_id)

            for challengeobject in challengeobject_list:
                if challengeobject.is_valid():
                    # challenge is still valid
                    otp_counter = self.check_answer(passw, challengeobject)
                    if otp_counter >= 0:
                        # We found the matching challenge, so lets return the
                        #  successful result and delete the challenge object.
                        challengeobject.delete()
                        break
                    else:
                        # increase the received_count
                        challengeobject.set_otp_status()

        self.challenge_janitor()
        return otp_counter

    @staticmethod
    def get_setting_type(key):
        """
        The setting type of questions is public, so that the user can also
        read the questions.

        :param key: The key of the setting
        :return: "public" string
        """
        if key.startswith("question.question."):
            return "public"
