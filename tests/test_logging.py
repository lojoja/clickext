# pylint: disable=c0114,c0116

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
@click.option("--usage", type=int)
def cmd(usage):
    raise click.ClickException("foo")


@pytest.mark.parametrize(
    ["args", "error"],
    [
        ([], "Error: foo\n"),
        (["--usage", "foo"], "Error: Invalid value for '--usage': 'foo' is not a valid integer.\n"),
    ],
)
def test_click_exception_logging(args, error):
    runner = CliRunner()
    result = runner.invoke(cmd, args)

    assert result.exit_code != 0
    assert result.output == error
