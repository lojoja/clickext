# pylint: disable=missing-function-docstring,missing-module-docstring

import logging

import click
import pytest

from clickext import init_logging


@pytest.mark.parametrize(
    ["exception", "msg", "output"],
    [
        (click.ClickException, "exception message", "Error: exception message\n"),
        (click.UsageError, "usage error message", "Error: usage error message\n"),
    ],
    ids=["click exception", "usage error"],
)
def test_unpatched_exception(capsys: pytest.CaptureFixture, exception: click.ClickException, msg: str, output: str):
    click.ClickException.logger = None  # type: ignore
    exception(msg).show()  # type: ignore
    captured = capsys.readouterr()
    assert captured.err == output


@pytest.mark.parametrize(
    ["exception", "msg", "output"],
    [
        (click.ClickException, "exception message", "Error: exception message\n"),
        (click.UsageError, "usage error message", "Error: usage error message\n"),
    ],
    ids=["click exception", "usage error"],
)
def test_patched_exception(capsys: pytest.CaptureFixture, exception: click.ClickException, msg: str, output: str):
    init_logging(logging.getLogger("test_exceptions"))
    exception(msg).show()  # type: ignore
    captured = capsys.readouterr()
    assert captured.err == output
