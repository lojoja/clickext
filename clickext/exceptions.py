"""
clickext.exceptions

Logger-aware exception handling.
"""

import logging
import typing as t

import click


def patch_exceptions(logger: logging.Logger) -> None:
    """Send click exception output to a logger.

    Patches `click.ClickException`, `click.UsageError`, and their children to override the default behavior of printing
    a message directly to the console. Instead, messages will be printed consistent with the current log level providing
    greater control of the program output.

    This function is called automatically by `clickext.init_logging` when the program logging is initialized. It should
    not be called manually.

    :param logger: The program logger. See `clickext.log.init_logging`.
    """
    click.ClickException.logger = logger  # pyright: ignore[reportAttributeAccessIssue]
    click.ClickException.show = _click_exception_patch
    click.UsageError.show = _click_usage_error_patch


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
