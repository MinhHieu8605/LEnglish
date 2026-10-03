from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.model import Base, TimeStampMixin


class WordList(Base, TimeStampMixin):
    """Represents a user's word-list collection."""

    __tablename__ = "WordList"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_word_lists_user_id_name"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)

    user = relationship("User", back_populates="word_lists")
    items = relationship(
        "WordListItem", back_populates="word_list", cascade="all, delete-orphan"
    )


class WordListItem(Base, TimeStampMixin):
    """Represents a vocabulary entry saved in a user's word list."""

    __tablename__ = "WordListItem"
    __table_args__ = (
        UniqueConstraint(
            "word_list_id",
            "vocabulary_id",
            name="uq_word_list_items_word_list_id_vocabulary_id",
        ),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    word_list_id = Column(
        Integer, ForeignKey("WordList.id", ondelete="CASCADE"), nullable=False
    )
    vocabulary_id = Column(
        Integer, ForeignKey("Vocabulary.id", ondelete="CASCADE"), nullable=False
    )
    source_subtitle_id = Column(
        Integer, ForeignKey("Subtitle.id", ondelete="SET NULL"), nullable=True
    )
    context_sentence = Column(Text)
    note = Column(Text)

    word_list = relationship("WordList", back_populates="items")
    vocabulary = relationship("Vocabulary", back_populates="word_list_items")
