# pylint: disable=c0114,c0116

import logging

import click
from click.testing import CliRunner
import pytest

from clickext import clickext


@pytest.mark.parametrize(
    ["level", "subs", "expected"],
    [
        (logging.CRITICAL, ("test",), "\x1b[31mCritical: \x1b[0mtest msg"),
        (logging.DEBUG, ("test",), "\x1b[34mDebug: \x1b[0mtest msg"),
        (logging.ERROR, ("test",), "\x1b[31mError: \x1b[0mtest msg"),
        (logging.WARNING, ("test",), "\x1b[33mWarning: \x1b[0mtest msg"),
    ],
    ids=["critical", "debug", "error", "warning"],
)
def test_format(level: int, subs: tuple, expected: str):
    formatter = clickext.Formatter()
    record = logging.LogRecord("foo", level, "path", 1, "%s msg", subs, None)

    assert formatter.format(record) == expected


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
