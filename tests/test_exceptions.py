# pylint: disable=missing-function-docstring,missing-module-docstring

import logging

import click
import pytest

from clickext.exceptions import patch_exceptions, _click_exception_patch, _click_usage_error_patch
from clickext.log import init_logging


def test_patch_exceptions(logger: logging.Logger):
    patch_exceptions(logger)
    assert click.ClickException.logger is logger  # pyright: ignore[reportAttributeAccessIssue]
    assert click.ClickException.show is _click_exception_patch
    assert click.UsageError.show is _click_usage_error_patch


def test__click_exception_patch(capsys: pytest.CaptureFixture, logger: logging.Logger):
    init_logging(logger)
    _click_exception_patch(click.ClickException("test"))
    assert capsys.readouterr().err == "Error: test\n"


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
