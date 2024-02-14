"""
clickext.exceptions

Logger-aware exception handling.
"""

from __future__ import annotations

import logging
import sys
import typing as t

import click

if t.TYPE_CHECKING:
    from types import TracebackType


def patch_exceptions(logger: logging.Logger) -> None:
    """Sends click and other uncaught exceptions to a logger.

    Patches `click.ClickException`, `click.UsageError`, their children, and `sys.excepthook` to override the default
    behavior of printing a message directly to the console. Instead, messages will be printed consistent with the
    current log level providing greater control of the program output. Exception information, including a traceback when
    available, will be printed if the log level is `logging.DEBUG`.

    This function is called automatically by `clickext.init_logging` when the program logging is initialized. It should
    not be called manually.

    :param logger: The program logger. See `clickext.log.init_logging`.
    """

    def excepthook(exc_type: type[BaseException], exc_value: BaseException, exc_traceback: TracebackType) -> None:
        exc_info = (exc_type, exc_value, exc_traceback)

        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(*exc_info)
            return

        logger.critical(str(exc_value), exc_info=exc_info if logger.level == logging.DEBUG else None)

    click.ClickException.logger = logger  # pyright: ignore[reportAttributeAccessIssue]
    click.ClickException.show = _click_exception_patch
    click.UsageError.show = _click_usage_error_patch
    sys.excepthook = excepthook


def _click_exception_patch(self: click.ClickException, file: t.Optional[t.IO] = None) -> None:
    """Patch for `click.ClickException.show` that sends output a logger."""
    file = click.get_text_stream("stderr") if file is None else file
    exc_info = (
        self
        if self.logger.getEffectiveLevel() == logging.DEBUG  # pyright: ignore[reportAttributeAccessIssue]
        else None
    )
    self.logger.error(self.format_message(), exc_info=exc_info)  # pyright: ignore[reportAttributeAccessIssue]


def _click_usage_error_patch(self: click.UsageError, file: t.Optional[t.IO] = None) -> None:
    """Patch for `click.UsageError.show` that sends output a logger."""
    file = click.get_text_stream("stderr") if file is None else file
    exc_info = (
        self
        if self.logger.getEffectiveLevel() == logging.DEBUG  # pyright: ignore[reportAttributeAccessIssue]
        else None
    )
    hint = ""

    if self.ctx is not None:
        hint = ""

        if self.ctx.command.get_help_option(self.ctx) is not None:
            hint = f"Try '{self.ctx.command_path} {self.ctx.help_option_names[0]}' for help.\n"

        click.echo(f"{self.ctx.get_usage()}\n{hint}", file=file, color=None)

    self.logger.error(self.format_message(), exc_info=exc_info)  # pyright: ignore[reportAttributeAccessIssue]
