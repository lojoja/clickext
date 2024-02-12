"""
clickext.exceptions

Logger-aware exception handling.
"""

import logging
import typing as t

import click


def patch_exceptions(logger: logging.Logger) -> None:
    """Send click exception output to a logger.

    By default, click exceptions print directly to the console and cannot be suppressed. Patched exceptions allow
    complete control of the console output verbosity statically or dynamically at runtime with the `clickext.verbose`
    and `clickext.verbosity` decorators.

    This function is called automatically by `clickext.init_logging`.

    Arguments:
        logger: The logger that click exception output should be routed to.
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
