import contextlib
import logging
import sys
import typing as t
from pathlib import Path

import click
import pytest


@pytest.fixture(autouse=True)
def reset_environment_fixture() -> t.Generator[None]:
    """Reset the global environment after each test."""
    _sys_excepthook = sys.excepthook
    _click_exception_show = click.ClickException.show
    _click_usage_error_show = click.UsageError.show

    yield

    sys.excepthook = _sys_excepthook
    click.ClickException.show = _click_exception_show
    click.UsageError.show = _click_usage_error_show

    with contextlib.suppress(AttributeError):
        for obj, name in [(click.ClickException, "logger"), (logging, "QUIET")]:
            delattr(obj, name)

    with contextlib.suppress(KeyError):
        for attr, key in [("_levelToName", 1000), ("_nameToLevel", "QUIET")]:
            del getattr(logging, attr)[key]

    logging.captureWarnings(False)  # noqa: FBT003
    logging.raiseExceptions = True
    logging.getLogger().handlers.clear()
    logging.getLogger().setLevel(logging.WARNING)


@pytest.fixture(name="logger")
def logger_fixture() -> t.Generator[logging.Logger]:
    """Create a clean logger and resets it after tests."""
    logger = logging.getLogger("test_logger")
    yield logger

    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)


@pytest.fixture(name="config", scope="session")
def config_fixture(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Create valid and invalid configuration files for tests.

    The fixture value is a mapping of "<type>_<validity>" string descriptors to file paths, e.g,
    `{"json_valid": Path("/path/to/valid.json")}`
    """
    data = {
        "ini_valid": "x",
        "ini_invalid": "x",
        "json_valid": '{"key": "default_value"}',
        "json_invalid": '{"key": "default_value}',
        "toml_valid": 'key = "default_value"',
        "toml_invalid": 'key = "default_value',
        "yaml_valid": "key: default_value",
        "yaml_invalid": "key: @default_value",
    }

    files = {}

    tmp_dir = tmp_path_factory.getbasetemp()

    for descriptor, content in data.items():
        ext, name = descriptor.split("_")
        file = tmp_dir / f"{name}.{ext}"
        file.write_text(content, encoding="utf8")
        files[descriptor] = file

    return files
