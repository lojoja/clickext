# pylint: disable=missing-module-docstring,missing-function-docstring

import logging
import typing as t

import pytest

from clickext.log import ColorFormatter, ConsoleHandler, init_logging, QUIET_LEVEL_NUM, QUIET_LEVEL_NAME


@pytest.fixture(name="logger")
def logger_fixture(monkeypatch: pytest.MonkeyPatch) -> t.Generator[logging.Logger, t.Any, t.Any]:
    """Resets logging and returns a "clean" logger for tests."""

    monkeypatch.delitem(logging._levelToName, QUIET_LEVEL_NUM, raising=False)  # pylint: disable=protected-access
    monkeypatch.delitem(logging._nameToLevel, QUIET_LEVEL_NAME, raising=False)  # pylint: disable=protected-access
    monkeypatch.delattr("clickext.log.logging.QUIET", raising=False)
    monkeypatch.setattr("click.ClickException.logger", None)

    try:
        delattr(logging, QUIET_LEVEL_NAME)
    except AttributeError:
        pass

    logger = logging.getLogger("test_logger")

    yield logger

    logger.handlers.clear()
    logger.setLevel(logging.WARNING)


@pytest.mark.parametrize(
    ["level", "ansi"],
    [
        (logging.DEBUG, "34m"),
        (logging.INFO, ""),
        (logging.WARNING, "33m"),
        (logging.ERROR, "31m"),
        (logging.CRITICAL, "31m"),
    ],
)
@pytest.mark.parametrize("exc_info", [True, False])
def test_color_formatter_format(exc_info: bool, level: int, ansi: str):
    record = logging.LogRecord("name", level, "path", 1, "msg", None, (None, None, None) if exc_info else None)
    formatter = ColorFormatter()

    if record.exc_info:
        assert formatter.format(record) == "msg\nNoneType: None"
    else:
        prefix = f"\x1b[{ansi}{logging.getLevelName(level).title()}:\x1b[0m " if ansi else ""
        assert formatter.format(record) == f"{prefix}msg"


@pytest.mark.parametrize("valid", [True, False])
def test_console_handler_emit(capsys: pytest.CaptureFixture, valid: bool):
    record = logging.LogRecord("name", logging.ERROR, "path", 1, "msg", None, None) if valid else None

    handler = ConsoleHandler()
    handler.setFormatter(ColorFormatter())
    handler.emit(record)  # type:ignore

    err = capsys.readouterr().err

    if valid:
        assert err == "Error: msg\n"
    else:
        assert err.startswith("--- Logging error ---\n")


@pytest.mark.parametrize("level", [logging.DEBUG, logging.INFO, logging.CRITICAL, QUIET_LEVEL_NUM])
def test_init_logging(capsys: pytest.CaptureFixture, logger: logging.Logger, level: int):
    init_logging(logger, level)

    logger.debug("debug")
    logger.info("info")
    logger.critical("critical")

    expected_out = ""
    expected_err = ""

    if logging.DEBUG >= level < logging.INFO:
        expected_out += "Debug: debug\n"
    if logging.INFO >= level < logging.WARNING:
        expected_out += "info\n"
    if logging.CRITICAL >= level < QUIET_LEVEL_NUM:
        expected_err = "Critical: critical\n"

    captured = capsys.readouterr()

    assert logger.getEffectiveLevel() == level
    assert captured.err == expected_err
    assert captured.out == expected_out


def test_init_logging_clears_handlers(logger: logging.Logger):
    logger.addHandler(logging.NullHandler())
    logger.addHandler(logging.StreamHandler())

    init_logging(logger)

    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], ConsoleHandler)
    assert isinstance(logger.handlers[0].formatter, ColorFormatter)


@pytest.mark.parametrize("is_set", [True, False])
def test_init_logging_creates_quiet_level(logger: logging.Logger, is_set: bool):
    if is_set:  # The quiet level should only be added if it doesn't already exist.
        logging.addLevelName(QUIET_LEVEL_NUM, QUIET_LEVEL_NAME)
        setattr(logging, QUIET_LEVEL_NAME, QUIET_LEVEL_NUM)

    init_logging(logger, QUIET_LEVEL_NUM)

    assert logging.getLevelName(QUIET_LEVEL_NUM) == QUIET_LEVEL_NAME
    assert getattr(logging, QUIET_LEVEL_NAME) == QUIET_LEVEL_NUM
