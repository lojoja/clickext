# pylint: disable=missing-function-docstring,missing-module-docstring

import logging

import click
from click.testing import CliRunner
import pytest
import pytest_mock

from clickext import ClickextCommand, init_logging, config_option, verbose_option, verbosity_option


test_logger = logging.getLogger("test_decorators")


@pytest.mark.parametrize(
    ["is_file", "require_config", "output"],
    [
        (True, False, "Error: Failed to read configuration file\n"),
        (False, True, "Error: Configuration file not found\n"),
        (False, False, "Config is None\n"),
    ],
    ids=["read error", "config not found (required)", "config not found (not required)"],
)
def test_config_error(mocker: pytest_mock.MockerFixture, is_file: bool, require_config: bool, output: str):
    mocker.patch("clickext.decorators.Path.is_file", return_value=is_file)
    mocker.patch("clickext.decorators.Path.read_text", side_effect=IOError)

    @click.command(cls=ClickextCommand)
    @config_option("config.json", require_config=require_config)
    @click.pass_obj
    def cmd(obj):
        click.echo(f"Config is {obj}")

    runner = CliRunner()
    result = runner.invoke(cmd)

    assert result.output == output


@pytest.mark.parametrize(
    ["file", "source", "output"],
    [
        ("config.json", '{"foo": "bar"}', "Config foo is bar\n"),
        ("config.json", '{"foo":"bar}', "Error: Failed to parse configuration file\n"),
        ("config.toml", 'foo="bar"', "Config foo is bar\n"),
        ("config.toml", 'foo="bar', "Error: Failed to parse configuration file\n"),
        ("config.yaml", "foo: bar", "Config foo is bar\n"),
        ("config.yaml", 'foo: "bar', "Error: Failed to parse configuration file\n"),
        ("config.yml", "foo: bar", "Config foo is bar\n"),
        ("config.yml", 'foo: "bar', "Error: Failed to parse configuration file\n"),
        ("config.conf", "foo", 'Error: Unknown configuration file format ".conf"\n'),
    ],
    ids=[
        "json (valid)",
        "json (invalid)",
        "toml (valid)",
        "toml (invalid)",
        "yaml (valid)",
        "yaml (invalid)",
        "yml (valid)",
        "yml (invalid)",
        "unknown format",
    ],
)
def test_config_parse(mocker: pytest_mock.MockerFixture, file: str, source: str, output: str):
    mocker.patch("clickext.decorators.Path.is_file", return_value=bool(source))
    mocker.patch("clickext.decorators.Path.read_text", return_value=source)

    @click.command(cls=ClickextCommand)
    @config_option(file)
    @click.pass_obj
    def cmd(obj):
        click.echo(f"Config foo is {obj['foo']}")

    runner = CliRunner()
    result = runner.invoke(cmd)

    assert result.output == output


def test_config_processor(mocker: pytest_mock.MockerFixture):
    mocker.patch("clickext.decorators.Path.is_file", return_value=True)
    mocker.patch("clickext.decorators.Path.read_text", return_value='{"foo": 100}')

    def config_processor(data):
        data["foo"] = data["foo"] * 5
        return data

    @click.command(cls=ClickextCommand)
    @config_option("config.json", processor=config_processor)
    @click.pass_obj
    def cmd(obj):
        click.echo(f"Processed config value is {obj['foo']}")

    runner = CliRunner()
    result = runner.invoke(cmd)

    assert result.output == "Processed config value is 500\n"


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
