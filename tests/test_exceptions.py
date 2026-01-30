import logging
import sys

import click
import pytest

from clickext.exceptions import _click_exception_patch, _click_usage_error_patch, _excepthook, patch_exceptions
from clickext.log import init_logging


def test_patch_exceptions_click_exceptions(logger: logging.Logger) -> None:
    patch_exceptions(logger)
    assert click.ClickException.logger is logger  # ty:ignore[unresolved-attribute]
    assert click.ClickException.show is _click_exception_patch
    assert click.UsageError.show is _click_usage_error_patch


@pytest.mark.parametrize("level", [logging.DEBUG, logging.INFO])
@pytest.mark.parametrize("exc_class", [ValueError, KeyboardInterrupt])
def test_patch_exceptions_sys_excepthook(
    capsys: pytest.CaptureFixture, logger: logging.Logger, exc_class: type[BaseException], level: int
) -> None:
    msg = "KeyboardInterrupt" if exc_class is KeyboardInterrupt else "msg"

    init_logging(logger, level)

    assert sys.excepthook is _excepthook

    try:
        raise exc_class(msg)
    except (ValueError, KeyboardInterrupt) as exc:
        _excepthook(type(exc), exc, exc.__traceback__)

    err = capsys.readouterr().err

    if level == logging.DEBUG:
        assert err.startswith(f"Critical: {msg}\nTraceback (most recent call last):")
    else:
        assert err == f"Critical: {msg}\n"


def test__click_exception_patch(capsys: pytest.CaptureFixture, logger: logging.Logger) -> None:
    init_logging(logger)
    _click_exception_patch(click.ClickException("test"))
    assert capsys.readouterr().err == "Error: test\n"


@pytest.mark.parametrize("level", [logging.DEBUG, logging.INFO])
def test__click_exception_patch_traceback(capsys: pytest.CaptureFixture, logger: logging.Logger, level: int) -> None:
    init_logging(logger, level)

    try:
        msg = "test"
        raise click.ClickException(msg)  # noqa: TRY301
    except click.ClickException as exc:
        exc.show()

    err = capsys.readouterr().err

    if level == logging.DEBUG:
        assert err.startswith("Error: test\nTraceback (most recent call last):")
    else:
        assert err == "Error: test\n"


@pytest.mark.parametrize("has_help", [True, False])
@pytest.mark.parametrize("has_context", [True, False])
def test__click_usage_error_patch(
    capsys: pytest.CaptureFixture, logger: logging.Logger, has_context: bool, has_help: bool
) -> None:
    ctx = None
    usage_message = ""

    if has_context:
        cmd = click.Command("foo", add_help_option=has_help)
        ctx = click.Context(cmd)
        usage_message = "Usage:  [OPTIONS]\n"

        if has_help:
            usage_message += "Try ' --help' for help.\n"

        usage_message += "\n"

    init_logging(logger)
    _click_usage_error_patch(click.UsageError("test", ctx))

    assert capsys.readouterr().err == f"{usage_message}Error: test\n"


@pytest.mark.parametrize("level", [logging.DEBUG, logging.INFO])
def test__click_usage_error_patch_traceback(capsys: pytest.CaptureFixture, logger: logging.Logger, level: int) -> None:
    init_logging(logger, level)

    try:
        msg = "test"
        raise click.UsageError(msg)  # noqa: TRY301
    except click.UsageError as exc:
        exc.show()

    err = capsys.readouterr().err

    if level == logging.DEBUG:
        assert err.startswith("Error: test\nTraceback (most recent call last):")
    else:
        assert err == "Error: test\n"
