from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.model import Base, TimeStampMixin


class Notebook(Base, TimeStampMixin):
    """Represents a user's word-list collection."""

    __tablename__ = "notebooks"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_notebooks_user_id_name"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)

    user = relationship("User", back_populates="notebooks")
    items = relationship(
        "NotebookItem", back_populates="notebook", cascade="all, delete-orphan"
    )


class NotebookItem(Base, TimeStampMixin):
    """Represents a vocabulary entry saved in a user's word list."""

    __tablename__ = "notebook_items"
    __table_args__ = (
        UniqueConstraint(
            "notebook_id",
            "vocabulary_id",
            name="uq_notebook_items_notebook_id_vocabulary_id",
        ),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    notebook_id = Column(
        Integer, ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False
    )
    vocabulary_id = Column(
        Integer, ForeignKey("vocabularies.id", ondelete="CASCADE"), nullable=False
    )
    source_subtitle_id = Column(
        Integer, ForeignKey("subtitles.id", ondelete="SET NULL"), nullable=True
    )
    context_sentence = Column(Text)
    note = Column(Text)

    notebook = relationship("Notebook", back_populates="items")
    vocabulary = relationship("Vocabulary", back_populates="notebook_items")
