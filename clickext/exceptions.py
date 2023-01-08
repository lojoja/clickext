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

    This function is called automatically by `clickext.log.init_logging`.

    Arguments:
        logger: The logger that should click exceptions should be routed to.
    """
    click.ClickException.logger = logger  # type: ignore


def show_exception_patch(self: click.ClickException, file: t.Optional[t.IO] = None) -> None:
    """Patch for `click.ClickException.show` to send messages to a logger, when configured."""
    file = click.get_text_stream("stderr") if file is None else file

    if getattr(self, "logger", None) is not None:
        self.logger.error(self.format_message())  # type: ignore
    else:
        click.echo(f"Error: {self.format_message()}", file=file)


def show_usage_error_patch(self: click.UsageError, file: t.Optional[t.IO] = None) -> None:
    """Patch for `click.UsageError.show` to send messages to a logger, when configured."""
    file = click.get_text_stream("stderr") if file is None else file

    if self.ctx is not None:
        hint = ""

        if self.ctx.command.get_help_option(self.ctx) is not None:
            hint = f"Try '{self.ctx.command_path} {self.ctx.help_option_names[0]}' for help.\n"

        click.echo(f"{self.ctx.get_usage()}\n{hint}", file=file, color=None)

    if getattr(self, "logger", None) is not None:
        self.logger.error(self.format_message())  # type: ignore
    else:
        click.echo(f"Error: {self.format_message()}", file=file)


click.ClickException.logger = None  # type: ignore
click.ClickException.show = show_exception_patch
click.UsageError.show = show_usage_error_patch
