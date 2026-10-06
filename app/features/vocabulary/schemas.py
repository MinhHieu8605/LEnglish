from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class VocabularyBookResponse(BaseModel):
    """
    Response schema for vocabulary books/collections.

    Attributes:
        id (int): The unique identifier of the record.
        name (str): The display name of the resource.
        slug (str): The URL slug identifying the resource.
        description (Optional[str]): The description of the resource.
        category (str): The vocabulary book's category.
        image_url (Optional[str]): The illustration URL, if available.
        created_time (datetime): The timestamp when the record was created.
    """

    id: int
    name: str
    slug: str
    description: Optional[str]
    category: str
    image_url: Optional[str]
    created_time: datetime


class VocabularyTopicResponse(BaseModel):
    """
    Response schema for topics within a book with user progress stats.

    Attributes:
        id (int): The unique identifier of the record.
        book_id (int): The identifier of the vocabulary book containing the topic.
        name (str): The display name of the resource.
        slug (str): The URL slug identifying the resource.
        order_num (int): The position of the word or topic in the ordered collection.
        word_count (int): The number of vocabulary entries in the collection.
        mastered_word_count (int): The number of words the user has mastered.
        learning_word_count (int): The number of words the user is currently learning.
        new_word_count (int): The number of words the user has not yet reviewed.
    """

    id: int
    book_id: int
    name: str
    slug: str
    order_num: int
    word_count: int
    mastered_word_count: int
    learning_word_count: int
    new_word_count: int


class TopicWordResponse(BaseModel):
    """
    Response schema for a word inside a topic, including user progress if any.

    Attributes:
        id (int): The unique identifier of the record.
        word (str): The vocabulary word.
        word_type (Optional[str]): The word's part of speech, if available.
        ipa (Optional[str]): The word's IPA pronunciation, if available.
        audio_url (Optional[str]): The pronunciation audio URL, if available.
        image_url (Optional[str]): The illustration URL, if available.
        definition_vi (Optional[str]): The Vietnamese definition of the word.
        example_sentence (Optional[str]): An English example sentence containing the
            word.
        example_translation_vi (Optional[str]): The Vietnamese translation of the
            example sentence.
        order_num (int): The position of the word or topic in the ordered collection.
        status (Optional[str]): The current learning or session state.
        repetition_count (int): The number of successful repetitions in the current
            review state.
        interval_days (int): The scheduled review interval in whole days.
        next_review_at (Optional[datetime]): The timestamp when the next review becomes
            due.
    """

    id: int
    word: str
    word_type: Optional[str]
    ipa: Optional[str]
    audio_url: Optional[str]
    image_url: Optional[str]
    definition_vi: Optional[str]
    example_sentence: Optional[str]
    example_translation_vi: Optional[str]
    order_num: int
    status: Optional[str] = None
    repetition_count: int = 0
    interval_days: int = 0
    next_review_at: Optional[datetime] = None
