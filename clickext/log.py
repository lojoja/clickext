"""
clickext.log

Logging and console output handling for clickext programs.
"""

import logging
import textwrap
import typing as t

import click

from .exceptions import patch_exceptions


QUIET_LEVEL_NAME = "QUIET"
QUIET_LEVEL_NUM = 1000


class Styles(t.TypedDict, total=False):
    """Style types for `click.style`"""

    fg: t.Optional[int | t.Tuple[int, int, int] | str]
    bg: t.Optional[int | t.Tuple[int, int, int] | str]
    bold: t.Optional[bool]
    dim: t.Optional[bool]
    underline: t.Optional[bool]
    overline: t.Optional[bool]
    italic: t.Optional[bool]
    blink: t.Optional[bool]
    reverse: t.Optional[bool]
    strikethrough: t.Optional[bool]
    reset: bool


class ConsoleFormatter(logging.Formatter):
    """Format log messages for the console.

    Messages are prefixed with the log level. Prefixes can be styled with all options available to `click.style`. To
    customize styling for one or more log levels, set the desired options in `ConsoleFormatter.styles`.

    Attributes:
        styles: A mapping of log levels to prefix display styles.
    """

    styles: dict[str, Styles] = {
        "critical": {"fg": "red"},
        "debug": {"fg": "blue"},
        "error": {"fg": "red"},
        "exception": {"fg": "red"},
        "info": {},
        "warning": {"fg": "yellow"},
    }

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage().strip()

        style = self.styles.get(record.levelname.lower())

        if style:
            prefix = click.style(f"{record.levelname.title()}:", **style)
            record.message = f"{prefix} {record.message}"
            record.message = textwrap.indent(
                record.message, " " * (len(record.levelname) + 2), lambda x: not x.startswith(prefix)
            )

        if record.exc_info:
            record.exc_text = self.formatException(record.exc_info)
            record.message = f"{record.message}\n{record.exc_text}"

        return record.message


class ColorFormatter(ConsoleFormatter):
    """For backwards compatibility; use `ConsoleFormatter` instead."""


class ConsoleHandler(logging.Handler):
    """Send log messages to the console.

    Attributes:
        stderr_levels: Log levels that should write to stderr instead of stdout.
    """

    stderr_levels = ["critical", "error", "exceptions", "warning"]

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            use_stderr = record.levelname.lower() in self.stderr_levels
            click.echo(msg, err=use_stderr)
        except Exception:  # pylint: disable=broad-except
            self.handleError(record)


def init_logging(logger: logging.Logger, level: int = logging.INFO) -> logging.Logger:
    """Initialize program logging.

    Configures the given logger for console output, with `ConsoleHandler` and `ConsoleFormatter`. `click.ClickException`
    and children are patched to send errors messages to the logger instead of printing to the console directly. If this
    function is not called `click.ClickException` error messages cannot be suppressed by changing the logger level.

    An additional log level is added during initialization and assigned to `logging.QUIET`. This level can be used to
    supress all console output.

    Arguments:
        logger: The logger to configure.
        level: The default log level to print (default: `logging.INFO`).
    """
    logger.handlers.clear()

    if not hasattr(logging, QUIET_LEVEL_NAME):
        logging.addLevelName(QUIET_LEVEL_NUM, QUIET_LEVEL_NAME)
        setattr(logging, QUIET_LEVEL_NAME, QUIET_LEVEL_NUM)

    handler = ConsoleHandler()
    handler.setFormatter(ConsoleFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)

    logging.raiseExceptions = logger.getEffectiveLevel() == logging.DEBUG

    patch_exceptions(logger)

    return logger
