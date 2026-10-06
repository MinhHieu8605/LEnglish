from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.model import Base, TimeStampMixin


class WordList(Base, TimeStampMixin):
    """
    Represents a user's word-list collection.

    Attributes:
        id (int): The unique identifier of the record.
        user_id (int): The identifier of the user who owns the record.
        name (str): The display name of the resource.
        description (Optional[str]): The description of the resource.
        user (User): The user account that owns the record.
        items (List[WordListItem]): The entries belonging to this collection or session.
    """

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
    """
    Represents a vocabulary entry saved in a user's word list.

    Attributes:
        id (int): The unique identifier of the record.
        word_list_id (int): The identifier of the word list containing the saved entry.
        vocabulary_id (int): The identifier of the associated vocabulary entry.
        source_subtitle_id (Optional[int]): The subtitle from which the word was saved,
            if any.
        context_sentence (Optional[str]): The source sentence retained with the saved
            word.
        note (Optional[str]): The user's note associated with this saved word.
        word_list (WordList): The personal word list containing the saved entry.
        vocabulary (Vocabulary): The vocabulary entry associated with the record.
    """

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
