import os
import sys
from functools import wraps


class PrettyPrinter:
    """
    Helper class to pretty print
    """

    _colors_enabled = True

    class Colors:
        """
        Color enum
        """
        RED = '\x1B[38;5;196m'
        GREEN = '\x1B[38;5;83m'
        ORANGE = '\x1B[38;5;214m'
        ENDC = '\x1B[0m'

    @classmethod
    def disable_colors(cls):
        cls._colors_enabled = False

    @classmethod
    def _format(cls, color, text):
        """
        Generic pretty print string formatter
        """
        if not cls._colors_enabled:
            color = ''
        return u"{}{}{}".format(color, text, cls.Colors.ENDC)

    @staticmethod
    def green(text):
        """
        Formats text as green
        """
        return PrettyPrinter._format(PrettyPrinter.Colors.GREEN, text)

    @staticmethod
    def red(text):
        """
        Formats text as red
        """
        return PrettyPrinter._format(PrettyPrinter.Colors.RED, text)

    @staticmethod
    def orange(text):
        """
        Formats text as orange
        """
        return PrettyPrinter._format(PrettyPrinter.Colors.ORANGE, text)

    @classmethod
    def println(cls, text=None):
        """
        Prints text as is with newline in the end
        """
        if text:
            sys.stdout.write(u"{}\n".format(text))
            sys.stdout.flush()
        else:
            sys.stdout.write(u"\n")
            sys.stdout.flush()

    @classmethod
    def pl_green(cls, text):
        """
        Prints text formatted as green
        """
        cls.println(cls.green(text))

    @classmethod
    def pl_red(cls, text):
        """
        Prints text formatted as red
        """
        cls.println(cls.red(text))

    @classmethod
    def pl_orange(cls, text):
        """
        Prints text formatted as orange
        """
        cls.println(cls.orange(text))


def check_root_privileges(func):
    """
    This function checks if the current user is root.
    If the user is not root it exits immediately.
    """
    @wraps(func)
    def do_root_check(*args, **kwargs):
        if os.getuid() != 0:
            # check if root user
            PrettyPrinter.pl_red("Root privileges are required to run this tool")
            sys.exit(1)
        return func(*args, **kwargs)
    return do_root_check
