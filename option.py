from typing import *

# Statics (just for type hinting)
T = TypeVar('T')

class Option(Generic[T]):
    @staticmethod
    def is_defined():
        raise NotImplementedError()

    @staticmethod
    def is_none():
        raise NotImplementedError()

    def get(self):
        raise NotImplementedError()

    def get_or(self, _):
        raise NotImplementedError()

    def then(self, _):
        raise NotImplementedError()

# Dynamics
class Non(Option[T]):
    @staticmethod
    def is_defined():
        return False

    @staticmethod
    def is_none():
        return True

    @staticmethod
    def get():
        raise RuntimeError("Unwrapping a None")

    def get_or(self, default):
        return default

    def __str__(self):
        return 'None'

    def __repr__(self):
        return str(self)

    def then(self, _):
        return self


class Some(Option[T]):
    def __init__(self, val):
        self.val = val

    @staticmethod
    def is_defined():
        return True

    @staticmethod
    def is_none():
        return False

    def get(self):
        return self.get_or(None)

    def get_or(self, _):
        return self.val

    def __str__(self):
        return f"Some({self.val})"

    def __repr__(self):
        return str(self)

    def then(self, f):
        return Some(f(self.val))
