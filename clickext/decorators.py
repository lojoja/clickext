"""
clickext.decorators

Argument and option decorators for clickext commands.
"""

import logging
import typing as t

import click

from .clickext import ClickextCommand


def verbose_option(
    logger: logging.Logger, *param_decls: str, **kwargs: t.Any
) -> t.Union[t.Callable[..., t.Any], ClickextCommand]:
    """Adds a verbose option.

    A flag to switch between standard output and verbose output. Output is handled by the given logger. The logger must
    be passed to `clickext.init_logging` before using the decorator.

    Arguments:
        logger: The logger instance to modify.
        param_decls: One or more option names. Defaults to "--verbose / -v".
        kwargs: Extra arguments passed to `click.option`.
    """

    def callback(ctx: click.Context, param: click.Parameter, value: bool) -> None:  # pylint: disable=unused-argument
        level = logging.DEBUG if value else logging.INFO
        logger.setLevel(level)

    if not param_decls:
        param_decls = ("--verbose", "-v")

    kwargs.setdefault("metavar", "LVL")
    kwargs.setdefault("expose_value", False)
    kwargs.setdefault("help", "Increase verbosity")
    kwargs["is_flag"] = True
    kwargs["flag_value"] = True
    kwargs["default"] = False
    kwargs["is_eager"] = True
    kwargs["callback"] = callback

    return click.option(*param_decls, **kwargs)


def verbosity_option(
    logger: logging.Logger, *param_decls: str, **kwargs: t.Any
) -> t.Union[t.Callable[..., t.Any], ClickextCommand]:
    """Adds a configurable verbosity option.

    Output is handled by the given logger. The logger must be passed to `clickext.init_logging` before using the
    decorator. Available verbosity levels are (from least to most verbose):

        - "QUIET"
        - "CRITICAL"
        - "ERROR"
        - "WARNING"
        - "INFO" (DEFAULT)
        - "DEBUG"

    Levels are case-insensitive.

    Arguments:
        logger: The logger instance to modify.
        param_decls: One or more option names. Defaults to "--verbosity / -v".
        kwargs: Extra arguments passed to `click.option`.
    """

    def callback(ctx: click.Context, param: click.Parameter, value: str) -> None:  # pylint: disable=unused-argument
        logger.setLevel(getattr(logging, value.upper()))

    if not param_decls:
        param_decls = ("--verbosity", "-v")

    kwargs.setdefault("default", "INFO")
    kwargs.setdefault("metavar", "LVL")
    kwargs.setdefault("expose_value", False)
    kwargs.setdefault("help", "Specify verbosity level")
    kwargs["is_eager"] = True
    kwargs["type"] = click.Choice(["QUIET", "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"], case_sensitive=False)
    kwargs["callback"] = callback

    return click.option(*param_decls, **kwargs)
