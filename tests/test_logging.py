# pylint: disable=missing-function-docstring,missing-module-docstring

import logging

import pytest

from clickext import init_logging, log


@pytest.mark.parametrize(
    ["level", "subs", "output"],
    [
        (logging.CRITICAL, ("test",), "\x1b[31mCritical: \x1b[0mtest msg"),
        (logging.DEBUG, ("test",), "\x1b[34mDebug: \x1b[0mtest msg"),
        (logging.INFO, ("test",), "test msg"),
        (logging.ERROR, ("test",), "\x1b[31mError: \x1b[0mtest msg"),
        (logging.WARNING, ("test",), "\x1b[33mWarning: \x1b[0mtest msg"),
    ],
    ids=["critical", "debug", "info", "error", "warning"],
)
def test_formatter(level: int, subs: tuple, output: str):
    formatter = log.ColorFormatter()
    record = logging.LogRecord("foo", level, "path", 1, "%s msg", subs, None)

    assert formatter.format(record) == output


@pytest.mark.parametrize(
    ["record", "output"],
    [
        (logging.LogRecord("foo", logging.ERROR, "path", 1, "msg", None, None), "Error: msg\n"),
        ("invalid record", "--- Logging error ---"),
    ],
    ids=["valid record", "invalid record"],
)
def test_handler(capsys: pytest.CaptureFixture, record: logging.LogRecord | None, output: str):
    handler = log.ConsoleHandler()
    handler.setFormatter(log.ColorFormatter())
    handler.emit(record)  # type: ignore
    captured = capsys.readouterr()
    assert captured.err.startswith(output)


def test_logger_init(capsys: pytest.CaptureFixture):
    logger = init_logging(logging.getLogger("test_logging"))
    logger.info("info message")
    logger.debug("debug message")
    captured = capsys.readouterr()
    assert captured.out == "info message\n"
    assert getattr(logging, log.QUIET_LEVEL_NAME) == log.QUIET_LEVEL_NUM
