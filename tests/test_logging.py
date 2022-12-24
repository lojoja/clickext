import logging

import click
from click.testing import CliRunner
import pytest

from clickext import clickext


@pytest.mark.parametrize(
    ["level", "msg", "expected"],
    [
        (logging.CRITICAL, "msg", "\x1b[31mCritical: \x1b[0mmsg"),
        (logging.DEBUG, "msg", "\x1b[34mDebug: \x1b[0mmsg"),
        (logging.ERROR, "msg", "\x1b[31mError: \x1b[0mmsg"),
        (logging.WARNING, "msg", "\x1b[33mWarning: \x1b[0mmsg"),
    ],
)
def test_format(level, msg, expected):
    formatter = clickext.Formatter()
    record = logging.LogRecord("foo", level, "path", 1, msg, None, None)
    result = formatter.format(record)

    assert result == expected


@pytest.mark.parametrize(
    ["record"], [(logging.LogRecord("foo", logging.ERROR, "path", 1, "msg", None, None),), ("invalid record",)]
)
def test_handle(record):
    handler = clickext.Handler()
    handler.setFormatter(clickext.Formatter())
    result = handler.emit(record)

    assert result == None


@click.command()
def cmd():
    raise click.ClickException("foo")


def test_click_exception_logging():
    runner = CliRunner()
    result = runner.invoke(cmd)

    assert result != 0
    assert result.output == "Error: foo\n"
