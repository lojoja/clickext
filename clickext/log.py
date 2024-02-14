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

     By default, "INFO" level messages are passed through as-is. All other levels are formatted with a level name
     prefix: "{level:} {msg}".

    :param prefix_styles: A mapping of log level numbers to `click.style` parameters used to style the prefix in the
    formatted message. Style parameters are merged with the defaults unless styles is set to `None` in which case
    messages for that level will not be prefixed with the level name. Unknown levels are silently ignored. Example:

    ```
    prefix_styles = {
        logging.CRITICAL: {"fg": "purple"}, // fg=purple (overrides default)
        logging.DEBUG: {"bg": "green"}, // fg=blue, bg=green (merged with default)
        logging.ERROR: None // (will not prefix or style ERROR level messages)
    }
    ```
    """

    _default_styles: dict[int, Styles] = {
        logging.CRITICAL: {"fg": "red"},
        logging.DEBUG: {"fg": "blue"},
        logging.ERROR: {"fg": "red"},
        logging.INFO: {},
        logging.WARNING: {"fg": "yellow"},
    }

    def __init__(self, *, prefix_styles: t.Optional[dict[int, t.Optional[Styles]]] = None):
        super().__init__()
        self.prefix_styles: dict[int, t.Optional[Styles]] = {}

        if prefix_styles is None:
            prefix_styles = {}

        for level, style in self._default_styles.items():
            style_override: t.Optional[Styles] = {}

            if level in prefix_styles:
                style_override = prefix_styles[level]

            self.prefix_styles[level] = {} if style_override is None else {**style, **style_override}

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage().strip()

        prefix_style = self.prefix_styles[record.levelno]

        if prefix_style:
            prefix = click.style(f"{record.levelname.title()}:", **prefix_style)
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

    Writes to stderr if the record level is `logging.WARNING` or greater, otherwise to stdout.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            click.echo(msg, err=record.levelno >= logging.WARNING)
        except Exception:  # pylint: disable=broad-except
            self.handleError(record)


def init_logging(
    logger: logging.Logger,
    level: int | str = logging.INFO,
    root_handlers: t.Optional[list[logging.Handler]] = None,
    prefix_styles: t.Optional[dict[int, t.Optional[Styles]]] = None,
) -> None:
    """Initialize program logging.

    Configures the root logger to handle all log records and warnings issued with `warnings.warn` with `ConsoleHandler`
    and the `ConsoleFormatter`. Existing handlers are removed from the root logger.

    `click.ClickException`, `click.UsageError`, and their children are patched so their message output is sent to a
    program logger instead of printing to the console directly so the output is formatted consistently and can
    conditionally supressed based on the log level.

    An additional log level is added during initialization and assigned to `logging.QUIET`. This level can be used to
    suppress all log record output.

    All informational messages must be sent to a logger since direct calls to `print`, `click.echo`, etc. cannot be
    captured or formatted. Generic messages can be logged at the `INFO` level which, by default, outputs the message
    as-received with no additional formatting. Non-informational messages that should always be displayed (e.g, the
    calculated result of the program) should continue to be sent with `click.echo`.

    :param logger: The program logger. Patched click exception messages will be sent to this logger in order to preserve
    the source of the message. This will usually be the logger corresponding to the program's entrypoint module.
    :param level: The log level to print (default: `logging.INFO`).
    :param root_handlers: Additional handlers to attach to the root logger.
    :param prefix_styles: Log level prefix display styles. See: `ConsoleFormatter` for format.
    """
    if not hasattr(logging, QUIET_LEVEL_NAME):
        logging.addLevelName(QUIET_LEVEL_NUM, QUIET_LEVEL_NAME)
        setattr(logging, QUIET_LEVEL_NAME, QUIET_LEVEL_NUM)

    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    if root_handlers is None:
        root_handlers = []

    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    console_formatter = ConsoleFormatter(prefix_styles=prefix_styles)
    console_handler = ConsoleHandler()
    console_handler.setFormatter(console_formatter)

    for handler in [console_handler, *root_handlers]:
        root_logger.addHandler(handler)

    root_logger.setLevel(level)

    logging.captureWarnings(True)
    logging.raiseExceptions = level == logging.DEBUG

    logger.setLevel(level)
    logger.propagate = True

    patch_exceptions(logger)
