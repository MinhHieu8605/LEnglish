from sqlalchemy import Column, ForeignKey, Index, Integer, String

from app.database.model import Base, TimeStampMixin


class Feedback(Base, TimeStampMixin):
    """
    Represents user feedback in the system.

    Inherits from:
        Base: The base class for SQLAlchemy models.
        TimeStampMixin: A mixin that adds created_at and updated_at timestamp columns.
    
    Attributes:
        id (int): The unique identifier of the feedback.
        user_id (int): The ID of the user who submitted the feedback.
        type (str): The type of feedback (e.g., bug report, feature request).
        title (str): The title of the feedback.
        description (str): A detailed description of the feedback.
    """

    __tablename__ = "Feedback"

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)

    __table_args__ = (
        Index("feedback_idx", "user_id", "type", postgresql_using="btree"),
    )
