from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator



class CreateWordListRequest(BaseModel):
    """
    Request for creating a personal word list.

    Attributes:
        name (str): The display name of the resource.
        description (Optional[str]): The description of the resource.
    """

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: str) -> str:
        """
        Remove surrounding whitespace from the list name.

        Args:
            value (str): The list name supplied before field validation.

        Returns:
            str: The list name with surrounding whitespace removed; other input passes
                through.
        """
        return value.strip() if isinstance(value, str) else value

    @field_validator("description", mode="before")
    @classmethod
    def strip_description(cls, value: Optional[str]) -> Optional[str]:
        """
        Trim the description and normalize blank text to ``None``.

        Args:
            value (Optional[str]): The optional list description supplied before field
                validation.

        Returns:
            Optional[str]: The trimmed description, or None for blank input; other input
                passes through.
        """
        if not isinstance(value, str):
            return value
        return value.strip() or None


class WordListResponse(BaseModel):
    """
    One personal word list and its saved-word count.

    Attributes:
        id (int): The unique identifier of the record.
        name (str): The display name of the resource.
        description (Optional[str]): The description of the resource.
        word_count (int): The number of vocabulary entries in the collection.
        created_time (Optional[datetime]): The timestamp when the record was created.
    """

    id: int
    name: str
    description: Optional[str]
    word_count: int
    created_time: Optional[datetime]


class WordDefinitionInput(BaseModel):
    """
    One dictionary definition submitted when saving a new word.

    Attributes:
        definition_vi (str): The Vietnamese definition of the word.
        example (Optional[str]): An English example illustrating the definition.
        example_vi (Optional[str]): The Vietnamese translation of the example.
    """

    definition_vi: str
    example: Optional[str] = None
    example_vi: Optional[str] = None


class WordMeaningInput(BaseModel):
    """
    One part-of-speech entry submitted when saving a new word.

    Attributes:
        part_of_speech (str): The grammatical category associated with the definitions.
        ipa (Optional[str]): The word's IPA pronunciation, if available.
        audio_url (Optional[str]): The pronunciation audio URL, if available.
        definitions (List[WordDefinitionInput]): The distinct definitions and examples
            for this part of speech.
    """

    part_of_speech: str
    ipa: Optional[str] = None
    audio_url: Optional[str] = None
    definitions: List[WordDefinitionInput]


class SaveWordRequest(BaseModel):
    """
    Request for manually saving a word or dictionary result.

    Attributes:
        word (str): The vocabulary word.
        translation_vi (Optional[str]): The Vietnamese translation of the source text or
            word.
        image_url (Optional[str]): The illustration URL, if available.
        meanings (List[WordMeaningInput]): The dictionary meanings supplied when saving
            a new word.
        source_subtitle_id (Optional[int]): The subtitle from which the word was saved,
            if any.
        context_sentence (Optional[str]): The source sentence retained with the saved
            word.
        note (Optional[str]): The user's note associated with this saved word.
    """

    word: str = Field(..., min_length=1, max_length=100)
    translation_vi: Optional[str] = Field(default=None, max_length=500)
    image_url: Optional[str] = Field(default=None, max_length=2048)
    meanings: List[WordMeaningInput] = Field(
        default_factory=list,
        description=(
            "Dictionary meanings returned by lookup when the word is not in the database"
        ),
    )
    source_subtitle_id: Optional[int] = Field(default=None, ge=1)
    context_sentence: Optional[str] = None
    note: Optional[str] = None

    @field_validator("word", mode="before")
    @classmethod
    def strip_word(cls, value: str) -> str:
        """
        Remove surrounding whitespace before validating a word.

        Args:
            value (str): The word supplied before field validation.

        Returns:
            str: The word with surrounding whitespace removed; other input passes
                through.
        """
        return value.strip() if isinstance(value, str) else value

    @field_validator(
        "translation_vi", "image_url", "context_sentence", "note", mode="before"
    )
    @classmethod
    def strip_optional_text(cls, value: Optional[str]) -> Optional[str]:
        """
        Trim optional text and normalize blank values to ``None``.

        Args:
            value (Optional[str]): The optional translation, image URL, context
                sentence, or note to normalize.

        Returns:
            Optional[str]: Trimmed optional text, or None for blank input; other input
                passes through.
        """
        if not isinstance(value, str):
            return value
        return value.strip() or None

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: Optional[str]) -> Optional[str]:
        """
        Only accept HTTPS image URLs, matching the manual-add form.

        Args:
            value (Optional[str]): The optional image URL to validate.

        Returns:
            Optional[str]: The validated HTTPS URL, or None if no image URL was
                supplied.

        Raises:
            ValueError: If a supplied image URL lacks an HTTPS scheme or a host.
        """
        if value is None:
            return None

        parsed = urlparse(value)
        if parsed.scheme.lower() != "https" or not parsed.netloc:
            raise ValueError("image_url must use HTTPS")
        return value


class SavedWordResponse(BaseModel):
    """
    A word explicitly saved in one user word list.

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
        created_time (Optional[datetime]): The timestamp when the record was created.
        word_list_item_id (int): The identifier of the saved-word association.
        word_list_id (int): The identifier of the word list containing the saved entry.
        source_subtitle_id (Optional[int]): The subtitle from which the word was saved,
            if any.
        context_sentence (Optional[str]): The source sentence retained with the saved
            word.
        note (Optional[str]): The user's note associated with this saved word.
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
    created_time: Optional[datetime]
    word_list_item_id: int
    word_list_id: int
    source_subtitle_id: Optional[int]
    context_sentence: Optional[str]
    note: Optional[str]


class SavedWordReviewResponse(SavedWordResponse):
    """
    A saved word together with its spaced-repetition progress.

    Attributes:
        status (str): The current learning or session state.
        ease_factor (float): The multiplier used to calculate future successful-review
            intervals.
        repetition_count (int): The number of successful repetitions in the current
            review state.
        interval_days (int): The scheduled review interval in whole days.
        next_review_at (Optional[datetime]): The timestamp when the next review becomes
            due.
        last_reviewed_at (Optional[datetime]): The timestamp of the most recent recorded
            review, if any.
        personal_note (Optional[str]): The user's personal vocabulary note.
    """

    status: str
    ease_factor: float
    repetition_count: int
    interval_days: int
    next_review_at: Optional[datetime]
    last_reviewed_at: Optional[datetime]
    personal_note: Optional[str]


class SavedWordFilter(BaseModel):
    """
    Pagination and filtering for words saved in one word list.

    Attributes:
        page (int): The current page number, starting at one.
        page_size (int): The maximum number of items returned per page.
        keyword (Optional[str]): The search keyword used to filter results.
    """

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    keyword: Optional[str] = Field(default=None, max_length=100)

    @field_validator("keyword", mode="before")
    @classmethod
    def strip_keyword(cls, value: Optional[str]) -> Optional[str]:
        """
        Trim a search keyword and normalize blank text to ``None``.

        Args:
            value (Optional[str]): Raw search keyword supplied by the client.

        Returns:
            Optional[str]: Trimmed keyword or ``None`` when it is blank.
        """
        if not isinstance(value, str):
            return value
        return value.strip() or None


class SavedWordListMeta(BaseModel):
    """
    Pagination metadata for a saved-word list.

    Attributes:
        total (int): The total number of matching items.
        page (int): The current page number, starting at one.
        page_size (int): The maximum number of items returned per page.
        pages (int): The total number of pages matching the filters.
    """

    total: int
    page: int
    page_size: int
    pages: int


class SavedWordListResponse(BaseModel):
    """
    Paginated words saved in one word list.

    Attributes:
        data (List[SavedWordResponse]): The ordered items included in the response.
        metadata (SavedWordListMeta): The pagination metadata for the response.
    """

    data: List[SavedWordResponse]
    metadata: SavedWordListMeta


class SavedWordsDueFilter(BaseModel):
    """
    Pagination for words that are due for review.

    Attributes:
        page (int): The current page number, starting at one.
        page_size (int): The maximum number of items returned per page.
    """

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)


class SavedWordsDueResponse(BaseModel):
    """
    Paginated words in a word list that are due for review.

    Attributes:
        data (List[SavedWordReviewResponse]): The ordered items included in the
            response.
        metadata (SavedWordListMeta): The pagination metadata for the response.
    """

    data: List[SavedWordReviewResponse]
    metadata: SavedWordListMeta
