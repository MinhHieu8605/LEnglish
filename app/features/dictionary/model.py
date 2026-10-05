from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database.model import Base, TimeStampMixin
from app.utils.constants import LookupType


class DictionaryLookup(Base, TimeStampMixin):
    """
    Represents a word lookup event (dictionary or translation).

    Attributes:
        id (int): The unique identifier of the lookup event.
        user_id (int): The user identifier.
        word (str): The word that was looked up.
        type (str): Lookup type (dictionary, translate).
        source_url (str): URL where the lookup occurred.
        context_sentence (str): Context sentence for the lookup.
        result (dict): Lookup result data in JSON format.
    """

    __tablename__ = "DictionaryLookup"
    __table_args__ = (Index("dictionary_lookups_idx", "user_id", "created_time"),)

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    word = Column(String, nullable=False)
    type = Column(String, nullable=False, default=LookupType.DICTIONARY.value)
    source_url = Column(String)
    context_sentence = Column(Text)
    result = Column(JSONB)

    user = relationship("User")
