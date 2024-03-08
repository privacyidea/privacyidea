"""
Generic container class that can hold token of any type, but does not have special operations.
"""
import logging

from privacyidea.lib.containerclass import ContainerClass
from privacyidea.lib.log import log_with

log = logging.getLogger(__name__)


class GenericContainer(ContainerClass):

    @log_with(log)
    def __init(self, db_container):
        super().__init__(db_container)
        self.type = "Generic"
