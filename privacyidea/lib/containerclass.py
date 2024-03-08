"""
Base class for token container.
"""
import logging

from privacyidea.lib.log import log_with

log = logging.getLogger(__name__)


class ContainerClass(object):

    tokens: list = []
    type = None

    @log_with(log)
    def __init__(self, db_container):
        self.tokens = db_container.tokens
        self.type = db_container.type
