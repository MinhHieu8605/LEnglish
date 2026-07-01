from typing import Any


class Singleton(type):
    """
    A metaclass for creating singleton classes.
    Ensures that only one instance of a class is created.
    """

    _instances: dict[type, Any] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
    

class BaseSingleton(metaclass=Singleton):
    """
    Base class for singleton classes.
    """

    pass
