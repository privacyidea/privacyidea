import logging
import re

log = logging.getLogger(__name__)


def validate_email(email):
    """
    Verify if the email is a gmail address.
    :param email: email address
    :return: True if valid, False otherwise
    """
    # regular expression for email validation
    regex = r'^[-\w\.]+@gmail.com$'
    if re.search(regex, email):
        return True
    else:
        return False
