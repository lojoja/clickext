"""
clickext.log

Console log output handling for click programs.
"""

import logging
import typing as t

import click


class ColorFormatter(logging.Formatter):
    """Stylize click messages.

    Messages are prefixed with the log level. Prefixes can be styled with all options available to `click.style`. To
    customize styling for one or more log levels, set the desired options in `ClickextFormatter.styles`.

    Attributes:
        styles: A mapping of log levels to display styles.
    """

    styles = {
        "critical": dict(fg="red"),
        "debug": dict(fg="blue"),
        "error": dict(fg="red"),
        "exception": dict(fg="red"),
        "warning": dict(fg="yellow"),
    }

    def format(self, record):
        if not record.exc_info:
            level = record.levelname.lower()
            msg = record.getMessage()

            if level in self.styles:
                prefix = click.style(f"{level.title()}: ", **self.styles[level])
                msg = "\n".join(f"{prefix}{line}" for line in msg.splitlines())

            return msg

        return logging.Formatter.format(self, record)


class ConsoleHandler(logging.Handler):
    """Handle click console messages.

    Attributes:
        stderr_levels: Log levels that should write to stderr.
    """

    stderr_levels = ["critical", "error", "exceptions", "warning"]

    def emit(self, record):
        try:
            msg = self.format(record)
            use_stderr = record.levelname.lower() in self.stderr_levels
            click.echo(msg, err=use_stderr, color=True)
        except Exception:  # pylint: disable=broad-except
            self.handleError(record)


def init_logger(logger: logging.Logger, redirect_exceptions: bool = True, level: int = logging.INFO) -> logging.Logger:
    """Configure logger for console output.

    Arguments:
        logger: The logger to configure.
        redirect_exceptions: Whether raised `click.ClickException`s messages should be handled by the logger.
        level: The default log level to emit (default: `logging.INFO`).
    """

    handler = ConsoleHandler()
    handler.setFormatter(ColorFormatter())

    logger.addHandler(handler)
    logger.setLevel(level)

    def error(self: click.ClickException, file: t.Optional[t.IO] = None) -> None:  # pylint: disable=unused-argument
        logger.error(self.format_message())

    def usage_error(self: click.UsageError, file: t.Optional[t.IO] = None) -> None:  # pylint: disable=unused-argument
        hint = ""

        if self.ctx is not None and self.ctx.command.get_help_option(self.ctx) is not None:
            hint = f"Try '{self.ctx.command_path} {self.ctx.help_option_names[0]}' for help.\n"

        if self.ctx is not None:
            click.echo(f"{self.ctx.get_usage()}\n{hint}")

        logger.error(self.format_message())

    if redirect_exceptions:
        click.ClickException.show = error
        click.UsageError.show = usage_error

    return logger
