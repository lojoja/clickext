# pylint: disable=missing-module-docstring,missing-function-docstring

import logging
import typing as t

import click
import pytest

from clickext.log import (
    ColorFormatter,
    ConsoleFormatter,
    ConsoleHandler,
    init_logging,
    QUIET_LEVEL_NUM,
    QUIET_LEVEL_NAME,
)


def test_color_formatter_inherits_console_formatter():
    assert issubclass(ColorFormatter, ConsoleFormatter)


@pytest.mark.parametrize("exc_info", [True, False])
@pytest.mark.parametrize(
    ["level", "color"],
    [
        (logging.DEBUG, "blue"),
        (logging.INFO, None),
        (logging.WARNING, "yellow"),
        (logging.ERROR, "red"),
        (logging.CRITICAL, "red"),
    ],
)
@pytest.mark.parametrize("message", ["line", "multi\nline", "  \nstripline \n"])
def test_console_formatter_format(message: str, level: int, color: t.Optional[None], exc_info: bool):
    record = logging.LogRecord("name", level, "path", 1, message, None, (None, None, None) if exc_info else None)
    expected = message.strip()

    if color:
        indent = " " * (len(record.levelname) + 2)
        expected = click.style(f"{record.levelname.title()}:", fg=color) + f" {expected}"
        expected = "\n".join([f"{indent if idx > 0 else ''}{line}" for idx, line in enumerate(expected.splitlines())])

    if exc_info:
        expected = f"{expected}\nNoneType: None"

    assert ConsoleFormatter().format(record) == expected


@pytest.mark.parametrize("exc", [True, False])
@pytest.mark.parametrize("valid", [True, False])
def test_console_handler_emit(capsys: pytest.CaptureFixture, valid: bool, exc: bool):
    logging.raiseExceptions = exc
    record = logging.LogRecord("name", logging.ERROR, "path", 1, "msg", None, None) if valid else None

    handler = ConsoleHandler()
    handler.setFormatter(ConsoleFormatter())
    handler.emit(record)  # type:ignore

    err = capsys.readouterr().err

    if valid:
        assert err == "Error: msg\n"
    elif exc:
        assert err.startswith("--- Logging error ---\n")
    else:
        assert err == ""


@pytest.mark.parametrize("level", [logging.DEBUG, "INFO", logging.INFO, logging.CRITICAL, QUIET_LEVEL_NUM])
def test_init_logging(capsys: pytest.CaptureFixture, logger: logging.Logger, level: int | str):
    init_logging(logger, level)

    logger.debug("debug")
    logger.info("info")
    logger.critical("critical")

    expected_level = level if isinstance(level, int) else logging.getLevelName(level)
    expected_out = ""
    expected_err = ""

    if logging.DEBUG >= expected_level < logging.INFO:
        expected_out += "Debug: debug\n"
    if logging.INFO >= expected_level < logging.WARNING:
        expected_out += "info\n"
    if logging.CRITICAL >= expected_level < QUIET_LEVEL_NUM:
        expected_err = "Critical: critical\n"

    captured = capsys.readouterr()

    assert logger.getEffectiveLevel() == expected_level
    assert captured.err == expected_err
    assert captured.out == expected_out


def test_init_logging_clears_handlers(logger: logging.Logger):
    logger.addHandler(logging.NullHandler())
    logger.addHandler(logging.StreamHandler())

    init_logging(logger)

    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], ConsoleHandler)
    assert isinstance(logger.handlers[0].formatter, ConsoleFormatter)


@pytest.mark.parametrize("is_set", [True, False])
def test_init_logging_creates_quiet_level(logger: logging.Logger, is_set: bool):
    if is_set:  # The quiet level should only be added if it doesn't already exist.
        logging.addLevelName(QUIET_LEVEL_NUM, QUIET_LEVEL_NAME)
        setattr(logging, QUIET_LEVEL_NAME, QUIET_LEVEL_NUM)

    init_logging(logger, QUIET_LEVEL_NUM)

    assert logging.getLevelName(QUIET_LEVEL_NUM) == QUIET_LEVEL_NAME
    assert getattr(logging, QUIET_LEVEL_NAME) == QUIET_LEVEL_NUM


@pytest.mark.parametrize("level", [logging.DEBUG, logging.INFO])
def test_init_logging_raise_exceptions(logger: logging.Logger, level: int):
    init_logging(logger, level)
    assert logging.raiseExceptions == (level == logging.DEBUG)
