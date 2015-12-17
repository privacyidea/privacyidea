.. _questionnaire_token:

Questionnaire Token
-------------------

.. index:: Questionnaire Token, Question Token

The administrator can define a list of questions and also how many answers to
the questions a user needs to define.

During enrollment of such a *question* type token the user answers at least as
many questions as specified with answers only he knows.

This token is a challenge response token.
During authentication the user must give the token PIN and the a random
question from the answered question is chosen. The user has to answer with
the same answer he defined earlier.

.. note:: If the administrator changes the questions _after_ a token was
   enrolled, the enrolled token still works with the old questions and answers.
   I.e. an enrolled token is not affected by changing the questions by the
   administrator.
