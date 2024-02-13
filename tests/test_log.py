# pylint: disable=missing-module-docstring,missing-function-docstring

from __future__ import annotations

import logging
import sys
import typing as t
import warnings

import click
import pytest
from pytest_mock import MockerFixture

from clickext.log import (
    ColorFormatter,
    ConsoleFormatter,
    ConsoleHandler,
    init_logging,
    QUIET_LEVEL_NUM,
    QUIET_LEVEL_NAME,
)

if t.TYPE_CHECKING:
    from logging import _SysExcInfoType
    from clickext.log import Styles


def test_color_formatter_inherits_console_formatter():
    assert issubclass(ColorFormatter, ConsoleFormatter)


@pytest.mark.parametrize("exc_info", [None, (None, None, None)])
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
def test_console_formatter_format(
    message: str, level: int, color: t.Optional[None], exc_info: t.Optional[_SysExcInfoType]
):
    record = logging.LogRecord("name", level, "path", 1, message, None, exc_info)
    expected = message.strip()

    if color:
        indent = " " * (len(record.levelname) + 2)
        expected = click.style(f"{record.levelname.title()}:", fg=color) + f" {expected}"
        expected = "\n".join([f"{indent if idx > 0 else ''}{line}" for idx, line in enumerate(expected.splitlines())])

    if exc_info:
        expected = f"{expected}\nNoneType: None"

    assert ConsoleFormatter().format(record) == expected


@pytest.mark.parametrize("styles", [None, {}, {"bg": "green"}, {"fg": "purple"}])
def test_console_formatter_merge_prefix_styles(styles: t.Optional[Styles]):
    style_overrides = {logging.CRITICAL: styles, 20000: None}
    formatter = ConsoleFormatter(prefix_styles=style_overrides)
    result = formatter.prefix_styles

    assert 20000 not in result

    if styles is None:
        assert result[logging.CRITICAL] == {}
    else:
        assert result[logging.CRITICAL] == {
            **formatter._default_styles[logging.CRITICAL],  # pylint: disable=protected-access
            **styles,
        }


@pytest.mark.parametrize("raise_exc", [True, False])
@pytest.mark.parametrize("valid", [True, False])
@pytest.mark.parametrize("level", [logging.INFO, logging.WARNING])
def test_console_handler_emit(capsys: pytest.CaptureFixture, level: int, valid: bool, raise_exc: bool):
    logging.raiseExceptions = raise_exc
    record = logging.LogRecord("name", level, "path", 1, "msg", None, None) if valid else None

    handler = ConsoleHandler()
    handler.setFormatter(ConsoleFormatter())
    handler.emit(record)  # type: ignore

    captured = capsys.readouterr()

    if valid:
        if level == logging.INFO:
            assert captured.out == "msg\n"
            assert captured.err == ""
        else:
            assert captured.out == ""
            assert captured.err == "Warning: msg\n"
    elif raise_exc:
        assert captured.err.startswith("--- Logging error ---\n")
        assert captured.out == ""
    else:
        assert captured.out == ""
        assert captured.err == ""


def test_init_logging_capture_warnings(capsys: pytest.CaptureFixture, logger: logging.Logger):
    init_logging(logger)

    with warnings.catch_warnings():
        warnings.simplefilter("default")
        warnings.warn("msg")

    assert capsys.readouterr().err.startswith(f"Warning: {__file__}:")


@pytest.mark.parametrize("exists", [True, False])
def test_init_logging_creates_quiet_level(logger: logging.Logger, exists: bool):
    if exists:  # The quiet level should only be added if it doesn't already exist.
        logging.addLevelName(QUIET_LEVEL_NUM, QUIET_LEVEL_NAME)
        setattr(logging, QUIET_LEVEL_NAME, QUIET_LEVEL_NUM)

    init_logging(logger, QUIET_LEVEL_NUM)

    assert logging.getLevelName(QUIET_LEVEL_NUM) == QUIET_LEVEL_NAME
    assert getattr(logging, QUIET_LEVEL_NAME) == QUIET_LEVEL_NUM


@pytest.mark.parametrize("level", [logging.DEBUG, "INFO", logging.INFO, logging.CRITICAL, QUIET_LEVEL_NUM])
def test_init_logging_level(capsys: pytest.CaptureFixture, logger: logging.Logger, level: int | str):
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

    assert captured.err == expected_err
    assert captured.out == expected_out


def test_init_logging_program_logger_config(logger: logging.Logger):
    logger.addHandler(logging.NullHandler())

    init_logging(logger, logging.DEBUG)

    assert logger.level == logging.DEBUG
    assert logger.propagate


@pytest.mark.parametrize("level", [logging.DEBUG, logging.INFO])
def test_init_logging_raise_exceptions(logger: logging.Logger, level: int):
    init_logging(logger, level)
    assert logging.raiseExceptions is (level == logging.DEBUG)


@pytest.mark.parametrize("handlers", [None, [logging.StreamHandler()]])
def test_init_logging_root_logger_config(logger: logging.Logger, handlers: t.Optional[list[logging.Handler]]):
    root_logger = logging.getLogger()
    root_logger.addHandler(logging.NullHandler())

    init_logging(logger, logging.DEBUG, root_handlers=handlers)

    assert len(root_logger.handlers) == 2 if handlers else 1
    assert root_logger.level == logging.DEBUG
    assert isinstance(root_logger.handlers[0], ConsoleHandler)
    assert isinstance(root_logger.handlers[0].formatter, ConsoleFormatter)

    if handlers:
        assert root_logger.handlers[1] is handlers[0]


@pytest.mark.parametrize("level", [logging.DEBUG, logging.INFO])
@pytest.mark.parametrize("exc_class", [ValueError, KeyboardInterrupt])
def test_init_logging_sys_excepthook(
    capsys: pytest.CaptureFixture, mocker: MockerFixture, logger: logging.Logger, exc_class: type[Exception], level: int
):
    mock_excepthook = mocker.patch("sys.__excepthook__")

    init_logging(logger, level)

    exc = exc_class("msg")
    exc_info = (type(exc), exc, exc.__traceback__)
    sys.excepthook(*exc_info)

    if exc_class is KeyboardInterrupt:
        assert mock_excepthook.called_once_with(*exc_info)
    else:
        expected = "Critical: msg"

        if level == logging.DEBUG:
            expected = f"{expected}\nValueError: msg"

        assert capsys.readouterr().err == f"{expected}\n"
        assert mock_excepthook.not_called()
