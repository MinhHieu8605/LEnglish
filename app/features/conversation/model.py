from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database.model import Base, TimeStampMixin
from app.utils.constants import ContentStatus, ConversationType, MessageRole


class Scenario(Base, TimeStampMixin):
    """
    Represents an AI conversation scenario template.

    Attributes:
        id (int): The unique identifier of the scenario.
        title (str): The scenario title.
        slug (str): The URL-friendly slug.
        description (str): The scenario description.
        difficulty (str): The difficulty level (A1, A2, B1, B2, C1, C2).
        character_name (str): Name of the AI character in this scenario.
        system_prompt (str): System prompt for the AI conversation.
        initial_message (str): Initial message from the AI.
        image_url (str): Scenario image URL.
        status (str): Content status (draft, published, archived).
        display_order (int): Display order for sorting.
    """
    __tablename__ = "Scenario"
    __table_args__ = (UniqueConstraint("slug", name="uq_scenarios_slug"),)
    id = Column(Integer, autoincrement=True, primary_key=True)
    title = Column(String, nullable=False)
    slug = Column(String, nullable=False)
    description = Column(Text)
    difficulty = Column(String, nullable=False)
    character_name = Column(String)
    system_prompt = Column(Text, nullable=False)
    initial_message = Column(Text)
    image_url = Column(String)
    status = Column(String, nullable=False, default=ContentStatus.DRAFT.value)

    conversations = relationship("Conversation", back_populates="scenario")
    display_order = Column(Integer, nullable=False, default=0)


class Conversation(Base, TimeStampMixin):
    """
    Represents an AI conversation session.

    Attributes:
        id (int): The unique identifier of the conversation.
        user_id (int): The user identifier.
        type (str): Conversation type (free, scenario, lesson).
        scenario_id (int): The scenario identifier (if type is scenario).
        lesson_id (int): The lesson identifier (if type is lesson).
        title (str): The conversation title.
    """
    __tablename__ = "Conversation"
    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False, default=ConversationType.FREE.value)
    scenario_id = Column(Integer, ForeignKey("Scenario.id", ondelete="SET NULL"), nullable=True)
    lesson_id = Column(Integer, ForeignKey("Lesson.id", ondelete="SET NULL"), nullable=True)
    title = Column(String)

    user = relationship("User", back_populates="conversations")
    scenario = relationship("Scenario", back_populates="conversations")
    lesson = relationship("Lesson", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_time")


class Message(Base, TimeStampMixin):
    """
    Represents a message in an AI conversation.

    Attributes:
        id (int): The unique identifier of the message.
        conversation_id (int): The conversation identifier.
        role (str): Message role (user, assistant, system).
        content (str): Message content.
        translation_vi (str): Vietnamese translation.
        suggestions (dict): Suggestions data in JSON format.
        correction (dict): Correction data in JSON format.
    """
    __tablename__ = "Message"
    __table_args__ = (Index("messages_idx", "conversation_id", "created_time"),)

    id = Column(Integer, autoincrement=True, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("Conversation.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False, default=MessageRole.USER.value)
    content = Column(Text, nullable=False)
    translation_vi = Column(Text)
    suggestions = Column(JSONB)
    correction = Column(JSONB)

    conversation = relationship("Conversation", back_populates="messages")
