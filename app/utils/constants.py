from enum import Enum, unique
from typing import Literal


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
class LessonSessionMode(Enum):
    DICTATION = "dictation"
    LISTENING = "listening"
    SHADOWING = "shadowing"
    QUIZ = "quiz"


@unique
class LessonSessionStatus(Enum):
    STARTED = "started"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


@unique
class VocabularyBookCategory(str, Enum):
    """
    Category tags for vocabulary books.

    Attributes:
        TOEIC (str): TOEIC test preparation vocabulary.
        IELTS (str): IELTS test preparation vocabulary.
        OXFORD (str): Oxford word lists (e.g. Oxford 5000).
        ACADEMIC (str): Academic / university-level vocabulary.
    """
    TOEIC = "toeic"
    IELTS = "ielts"
    OXFORD = "oxford"
    ACADEMIC = "academic"


@unique
class WordType(Enum):
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PREPOSITION = "preposition"
    CONJUNCTION = "conjunction"
    PRONOUN = "pronoun"
    INTERJECTION = "interjection"
    DETERMINER = "determiner"
    EXCLAMATION = "exclamation"


@unique
class WordStatus(Enum):
    """
    Learning stage of a word in a user's spaced-repetition progress.

    Attributes:
        NEW: Saved but not reviewed yet.
        LEARNING: In the initial learning reviews.
        REVIEW: Learned and following the regular review schedule.
        MASTERED: Considered retained after meeting the mastery threshold.
        IGNORED: Excluded from learning and review queues.
    """

    NEW = "new"
    LEARNING = "learning"
    REVIEW = "review"
    MASTERED = "mastered"
    IGNORED = "ignored"


@unique
class ReviewRating(Enum):
    """Recall quality used to calculate the next SRS review time."""

    AGAIN = "again"
    HARD = "hard"
    GOOD = "good"
    EASY = "easy"


@unique
class ReviewMode(str, Enum):
    """Mode used to review vocabulary."""

    FLASHCARD = "flashcard"
    TYPING = "typing"
    CLOZE = "cloze"


@unique
class ReviewScope(str, Enum):
    """Words included in a vocabulary review queue."""

    DUE = "due"
    ALL = "all"


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

    MSG_UNAUTHORIZED = "You are not authorized to access this resource."


class SortOrder(str, Enum):
    """
    Defines the available sort orders.
    """
    ASCEND= "ascend"
    DESCEND = "descend"


class FeedbackType(str, Enum):
    """
    Defines the available feedback types.

    Attributes:
        BUG (str): Feedback related to a bug.
        FEATURE_REQUEST (str): Feedback requesting a new feature.
        OTHER (str): Other types of feedback.
    """
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    IMPROVEMENT = "improvement"
    OTHER = "other"


class FeedbackStatus(str, Enum):
    """
    Defines the available feedback statuses.

    Attributes:
        IN_REVIEW (str): Feedback that is pending review.
        NEW (str): Feedback that is new.
        RESOLVED (str): Feedback that has been resolved.
        CLOSED (str): Feedback that has been closed without resolution.
    """
    IN_REVIEW = "in_review"
    NEW = "new"
    RESOLVED = "resolved"
    CLOSED = "closed"


class FeedbackFilter(object):
    """
    Defines the available feedback filter options.
    """

    TYPE = "type"
    STATUS = "status"
    KEYWORD = "keyword"
    FROM_DATE = "from_date"
    TO_DATE = "to_date"


class FeedbackAttachmentType(str, Enum):
    """
    Contains the available attachment types for feedback.
    """

    FEEDBACK = "feedback"
    RESPONSE = "response"


class FileMode(object):
    """
    Defines the available file modes for reading and writing files.
    """

    READ: Literal["r"] = "r"
    READ_BINARY: Literal["rb"] = "rb"
    READ_WRITE: Literal["r+"] = "r+"
    READ_WRITE_BINARY: Literal["r+b"] = "r+b"

    WRITE: Literal["w"] = "w"
    WRITE_BINARY: Literal["wb"] = "wb"


class FileType(object):
    """
    Defines the available file types for various document formats.
    """

    PDF = ".pdf"
    CSV = ".csv"
    DOCX = ".docx"
    DOC = ".doc"
    XLSX = ".xlsx"
    XLS = ".xls"
    PPTX = ".pptx"
    PPT = ".ppt"
    TXT = ".txt"
    MD = ".md"
    HTML = ".html"
    PNG = ".png"
    JPG = ".jpg"
    JPEG = ".jpeg"
    XLSM = ".xlsm"
    CSVX = ".csvx"


class FileSizeLimit(object):
    """
    File size limits for various file types in bytes.
    """

    _KB = 1024
    _MB = 1024 * _KB

    SIZE_1MB = 1 * _MB
    SIZE_5MB = 5 * _MB
    SIZE_10MB = 10 * _MB
    SIZE_20MB = 20 * _MB
    SIZE_50MB = 50 * _MB
    SIZE_100MB = 100 * _MB


class FileConstants(int, Enum):
    """
    Constants for file operations.
    """

    MAX_FILENAME_LENGTH = 255
    SHORT_UUID_LENGTH = 22
