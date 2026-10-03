from enum import Enum
from typing import List, Union


def _as_list(value: Union[str, Enum, List[Union[str, Enum]]]) -> List[str]:
    """
    Converts a string or a list of strings into a list of strings.

    Args:
        value (Union[str, List[str]]): The value to convert. Can be a single string or a list of strings.

    Returns:
        List[str]: A list of strings.
    """
    values = value if isinstance(value, list) else [value]
    return [item.value if isinstance(item, Enum) else item for item in values]
