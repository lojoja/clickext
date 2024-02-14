# pylint: disable=missing-module-docstring,missing-function-docstring

import logging
import sys

import click
import pytest
from pytest_mock import MockerFixture

from clickext.exceptions import patch_exceptions, _click_exception_patch, _click_usage_error_patch
from clickext.log import init_logging


def test_patch_exceptions_click_exceptions(logger: logging.Logger):
    patch_exceptions(logger)
    assert click.ClickException.logger is logger  # pyright: ignore[reportAttributeAccessIssue]
    assert click.ClickException.show is _click_exception_patch
    assert click.UsageError.show is _click_usage_error_patch


@pytest.mark.parametrize("level", [logging.DEBUG, logging.INFO])
@pytest.mark.parametrize("exc_class", [ValueError, KeyboardInterrupt])
def test_patch_exceptions_sys_excepthook(
    capsys: pytest.CaptureFixture, mocker: MockerFixture, logger: logging.Logger, exc_class: type[Exception], level: int
):
    mock_excepthook = mocker.patch("sys.__excepthook__")

    init_logging(logger, level)

    exc = exc_class("msg")
    exc_info = (type(exc), exc, exc.__traceback__)
    sys.excepthook(*exc_info)

    if exc_class is KeyboardInterrupt:
        assert mock_excepthook.called_once_with(*exc_info)
    else:
        expected = "Critical: msg"

        if level == logging.DEBUG:
            expected = f"{expected}\nValueError: msg"

        assert capsys.readouterr().err == f"{expected}\n"
        assert mock_excepthook.not_called()


def test__click_exception_patch(capsys: pytest.CaptureFixture, logger: logging.Logger):
    init_logging(logger)
    _click_exception_patch(click.ClickException("test"))
    assert capsys.readouterr().err == "Error: test\n"


@pytest.mark.parametrize("level", [logging.DEBUG, logging.INFO])
def test__click_exception_patch_traceback(capsys: pytest.CaptureFixture, logger: logging.Logger, level: int):
    init_logging(logger, level)

    try:
        raise click.ClickException("test")
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
):
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
def test__click_usage_error_patch_traceback(capsys: pytest.CaptureFixture, logger: logging.Logger, level: int):
    init_logging(logger, level)

    try:
        raise click.UsageError("test")
    except click.UsageError as exc:
        exc.show()

    err = capsys.readouterr().err

    if level == logging.DEBUG:
        assert err.startswith("Error: test\nTraceback (most recent call last):")
    else:
        assert err == "Error: test\n"
