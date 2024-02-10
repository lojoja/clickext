# pylint: disable=missing-module-docstring,missing-function-docstring

import logging

import pytest

from clickext.log import ColorFormatter, ConsoleHandler, init_logging, QUIET_LEVEL_NUM, QUIET_LEVEL_NAME


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


@pytest.mark.parametrize("level", [logging.DEBUG, logging.INFO, QUIET_LEVEL_NUM])
def test_init_logging(capsys: pytest.CaptureFixture, level: int):
    logger = logging.getLogger(f"test_init_logging_{level}")
    init_logging(logger, level)

    logger.debug("debug")
    logger.info("info")

    expected = ""

    if level <= logging.DEBUG:
        expected += "Debug: debug\n"

    if level <= logging.INFO:
        expected += "info\n"

    assert logger.getEffectiveLevel() == level
    assert capsys.readouterr().out == expected


def test_init_logging_clears_handlers():
    logger = logging.getLogger("test_init_logging_clears_handlers")
    logger.addHandler(logging.NullHandler())
    logger.addHandler(logging.StreamHandler())

    init_logging(logger)

    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], ConsoleHandler)
    assert isinstance(logger.handlers[0].formatter, ColorFormatter)


def test_init_logging_quiet_level(capsys: pytest.CaptureFixture):
    try:
        delattr(logging, QUIET_LEVEL_NAME)  # this may have been set by other tests, so delete it
    except AttributeError:
        pass
    finally:
        assert not hasattr(logging, QUIET_LEVEL_NAME)

    logger = logging.getLogger("test_init_logging_quiet_level")
    init_logging(logger, QUIET_LEVEL_NUM)

    assert logging.getLevelName(QUIET_LEVEL_NUM) == QUIET_LEVEL_NAME
    assert getattr(logging, QUIET_LEVEL_NAME) == QUIET_LEVEL_NUM

    logger.critical("critical")
    assert all(i == "" for i in capsys.readouterr())
