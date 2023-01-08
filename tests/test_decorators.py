# pylint: disable=missing-function-docstring,missing-module-docstring

import logging

import click
from click.testing import CliRunner
import pytest

from clickext import ClickextCommand, init_logging, verbose_option, verbosity_option


test_logger = logging.getLogger("test_decorators")


@pytest.mark.parametrize(
    ["args", "level", "output"],
    [([], logging.INFO, "visible message\n"), (["--verbose"], logging.DEBUG, "Debug: visible message\n")],
    ids=["not verbose", "verbose"],
)
def test_verbose(args: list[str], level: int, output: str):  # pylint: disable=redefined-outer-name
    init_logging(test_logger)

    @click.command(cls=ClickextCommand)
    @verbose_option(test_logger)
    def cmd():
        test_logger.log(level, "visible message")
        test_logger.log(level - 5, "hidden message")

    runner = CliRunner()
    result = runner.invoke(cmd, args)

    assert test_logger.getEffectiveLevel() == level
    assert result.output == output


@pytest.mark.parametrize(
    ["args", "level", "output"],
    [
        (["--verbosity", "debug"], logging.DEBUG, "Debug: visible message\n"),
        ([], logging.INFO, "visible message\n"),
        (["--verbosity", "INFO"], logging.INFO, "visible message\n"),
        (["--verbosity", "WARNING"], logging.WARNING, "Warning: visible message\n"),
        (["--verbosity", "ERROR"], logging.ERROR, "Error: visible message\n"),
        (["--verbosity", "critical"], logging.CRITICAL, "Critical: visible message\n"),
        (["--verbosity", "QUIET"], 1000, ""),
        (["--verbosity", "xyz"], logging.INFO, "Invalid value for '--verbosity'"),
    ],
    ids=["debug", "info (default)", "info", "warning", "error", "critical", "quiet", "invalid"],
)
def test_verbosity(args: list[str], level: int, output: str):  # pylint: disable=redefined-outer-name
    init_logging(test_logger)

    @click.command(cls=ClickextCommand)
    @verbosity_option(test_logger)
    def cmd():
        test_logger.log(level, "visible message")
        test_logger.log(level - 5, "hidden message")

    runner = CliRunner()
    result = runner.invoke(cmd, args)

    assert test_logger.getEffectiveLevel() == level
    assert output in result.output
