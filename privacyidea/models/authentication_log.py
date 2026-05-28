from sqlalchemy import Integer
from sqlalchemy.orm import mapped_column, Mapped

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin


class AuthenticationLog(MethodsMixin, db.Model):
    """

    """
    __tablename__ = "authentication_log"
    id: Mapped[int] = mapped_column("id", Integer, primary_key=True)
