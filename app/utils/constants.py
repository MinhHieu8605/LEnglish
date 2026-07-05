from email.policy import default
from enum import Enum, unique


@unique
class Role(Enum):
    """
    Defines the available user roles.

    Attributes:
        ADMIN (str): The administrator role.
        USER (str): The default user role.
    """
    ADMIN = "admin"
    USER = "user"


@unique
class UserStatus(str, Enum):
    """
    Defines the available user statuses.

    Attributes:
        ACTIVE (str): The user is active.
        INACTIVE (str): The user is inactive.
    """
    ACTIVE = "active"
    INACTIVE = "inactive"


@unique
class TokenType(Enum):
    """
    Defines the available token types.

    Attributes:
        REFRESH (int): The refresh token type.
        ACCESS (int): The access token type.
    """
    REFRESH = 1
    ACCESS = 2


@unique
class SubtitleDisplay(Enum):
    EN = "en"
    VI = "vi"
    BOTH = "both"
    HIDDEN = "hidden"


@unique
class DifficultyLevel(Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


@unique
class ContentStatus(Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


@unique
class TagType(Enum):
    TOPIC = "topic"
    SKILL = "skill"
    ACCENT = "accent"
    SOURCE = "source"
    GRAMMAR = "grammar"


@unique
class PracticeMode(Enum):
    DICTATION = "dictation"
    LISTENING = "listening"
    SHADOWING = "shadowing"
    QUIZ = "quiz"


@unique
class PracticeStatus(Enum):
    STARTED = "started"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


@unique
class WordType(Enum):
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PHRASE = "phrase"
    IDIOM = "idiom"
    OTHER = "other"


@unique
class WordStatus(Enum):
    LEARNING = "learning"
    REVIEWING = "reviewing"
    MASTERED = "mastered"
    IGNORED = "ignored"


@unique
class ReviewRating(Enum):
    AGAIN = "again"
    HARD = "hard"
    GOOD = "good"
    EASY = "easy"


@unique
class ConversationType(Enum):
    FREE = "free"
    SCENARIO = "scenario"
    LESSON = "lesson"


@unique
class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@unique
class ActivityType(Enum):
    LESSON_VIEWED = "lesson_viewed"
    LESSON_COMPLETED = "lesson_completed"
    PRACTICE_COMPLETED = "practice_completed"
    WORD_SAVED = "word_saved"
    WORD_REVIEWED = "word_reviewed"
    AI_CHAT = "ai_chat"
    LOOKUP = "lookup"


@unique
class NotificationType(Enum):
    STREAK_REMINDER = "streak_reminder"
    REVIEW_DUE = "review_due"
    ACHIEVEMENT = "achievement"
    SYSTEM = "system"


@unique
class LookupType(Enum):
    DICTIONARY = "dictionary"
    TRANSLATE = "translate"


class Message(object):
    """
    A class containing predefind messages strings.
    """
    # Login
    MSG_LOGIN_WRONG_EMAIL = "Incorrect email. Please check and try again."
    MSG_LOGIN_WRONG_PASSWORD = "Incorrect password. Please check and try again."
    MSG_LOGIN_WRONG_CREDENTIALS = "You have entered incorrect login credentials. Please check again."
    MSG_LOGIN_ACCOUNT_DELETED = "Your account has been deleted. Please contact support for assistance."
    MSG_LOGIN_INVALID_TOKEN_UNAUTHORIZED = "Invalid token. User is not authorized."
    MSG_LOGIN_INVALID_TOKEN = "Invalid token. Please log in again."

    # Logout
    MSG_LOGOUT_SUCCESS = "You have been successfully logged out."

    # Register
    MSG_REGISTER_EMAIL_EXIST = "This email is already registered. Please use a different email."
    MSG_REGISTER_SUCCESS = "You have been successfully registered."

    # NOT FOUND
    MSG_NOT_FOUND = "Not found."