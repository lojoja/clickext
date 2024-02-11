# pylint: disable=missing-module-docstring,missing-function-docstring

import logging
import typing as t

import click
import pytest


@pytest.fixture(autouse=True)
def reset_environment_fixture() -> t.Generator[None, None, None]:
    """Resets the global environment after each test."""
    _click_exception_show = click.ClickException.show
    _click_usage_error_show = click.UsageError.show

    yield

    click.ClickException.show = _click_exception_show
    click.UsageError.show = _click_usage_error_show

    for obj, name in [(click.ClickException, "logger"), (logging, "QUIET")]:
        try:
            delattr(obj, name)
        except AttributeError:
            pass

    for attr, key in [("_levelToName", 1000), ("_nameToLevel", "QUIET")]:
        try:
            del getattr(logging, attr)[key]
        except KeyError:
            pass

    logging.raiseExceptions = True


@pytest.fixture(name="logger")
def logger_fixture() -> t.Generator[logging.Logger, None, None]:
    """Creates a clean logger and resets it after tests."""
    logger = logging.getLogger("test_logger")
    yield logger

    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
