from sqlalchemy import Column, ForeignKey, Index, Integer, UnicodeText
from sqlalchemy.orm import relationship

from app.database.model import Base, TimeStampMixin
from app.utils.constants import TokenType


class Token(Base, TimeStampMixin):
    """
    Represents an authentication token assigned to a user.

    Attributes:
        id (int): The unique identifier of the token.
        user_id (int): The unique identifier of the related user.
        token (str): The authentication token value.
    """
    __tablename__ = "tokens"

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(UnicodeText, nullable=False, unique=True)
    token_type = Column(Integer, nullable=False, default=TokenType.REFRESH.value)

    user = relationship("User", back_populates="tokens")

    __table__args__ = (
        Index("token_idx_token", "token", "token_type", postgresql_using="btree"),
    )
