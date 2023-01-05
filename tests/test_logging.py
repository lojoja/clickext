# pylint: disable=missing-function-docstring,missing-module-docstring

import logging

import click
from click.testing import CliRunner
import pytest

from clickext import init_logger, log


@pytest.mark.parametrize(
    ["level", "subs", "expected"],
    [
        (logging.CRITICAL, ("test",), "\x1b[31mCritical: \x1b[0mtest msg"),
        (logging.DEBUG, ("test",), "\x1b[34mDebug: \x1b[0mtest msg"),
        (logging.INFO, ("test",), "test msg"),
        (logging.ERROR, ("test",), "\x1b[31mError: \x1b[0mtest msg"),
        (logging.WARNING, ("test",), "\x1b[33mWarning: \x1b[0mtest msg"),
    ],
    ids=["critical", "debug", "info", "error", "warning"],
)
def test_formatter(level: int, subs: tuple, expected: str):
    formatter = log.ColorFormatter()
    record = logging.LogRecord("foo", level, "path", 1, "%s msg", subs, None)

    assert formatter.format(record) == expected


@pytest.mark.parametrize(
    ["record"],
    [(logging.LogRecord("foo", logging.ERROR, "path", 1, "msg", None, None),), ("invalid record",)],
    ids=["valid record", "invalid record"],
)
def test_handler(capsys: pytest.CaptureFixture, record: logging.LogRecord | None):
    handler = log.ConsoleHandler()
    handler.setFormatter(log.ColorFormatter())

    assert handler.emit(record) is None  # type: ignore

    if isinstance(record, logging.LogRecord):
        captured = capsys.readouterr()
        assert captured.err == "\x1b[31mError: \x1b[0mmsg\n"


def test_logger_init(
    capsys: pytest.CaptureFixture,
):
    logger = logging.getLogger("logger_init")
    init_logger(logger, redirect_exceptions=False)
    logger.info("foobar")
    captured = capsys.readouterr()
    assert captured.out == "foobar\n"

    logger.handlers = []  # Prevent duplicate handlers in tests


@pytest.mark.parametrize(["args"], [([],), (["--foo"],)])
def test_exception_overrides(args: list[str]):
    logger = logging.getLogger("exc_override")
    init_logger(logger)

    @click.command()
    def cmd():
        raise click.ClickException("foo")

    runner = CliRunner()
    result = runner.invoke(cmd, args, color=True)

    if args:
        assert (
            result.output
            == "Usage: cmd [OPTIONS]\nTry 'cmd --help' for help.\n\n\x1b[31mError: \x1b[0mNo such option: --foo\n"
        )
    else:
        assert result.output == "\x1b[31mError: \x1b[0mfoo\n"

    logger.handlers = []  # Prevent duplicate handlers in tests
