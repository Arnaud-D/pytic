import os

name = ".token"


class TokenExistsError(Exception):
    """Exception raised when attempting the creation of an already existing token."""
    def __init__(self, message):
        self.message = message


def create():
    """Create the token."""
    try:
        f = open(name, "x")
    except OSError:
        raise TokenExistsError("a token named '{}' already exists".format(name))
    else:
        f.close()


def delete():
    """Delete the token."""
    os.remove(name)


def exists():
    """Determine whether the token file exists."""
    return name in os.listdir()
