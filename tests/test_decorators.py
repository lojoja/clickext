# pylint: disable=missing-module-docstring,missing-function-docstring

import logging
from pathlib import Path
import typing as t

import click
from click.testing import CliRunner
import pytest
from pytest_mock import MockerFixture

from clickext.core import ClickextCommand
from clickext.decorators import config_option, verbose_option, verbosity_option
from clickext.log import QUIET_LEVEL_NAME, QUIET_LEVEL_NUM


@pytest.mark.parametrize("param_type_str", [True, False])
@pytest.mark.parametrize("error", [True, False])
def test_config_option_file_read(mocker: MockerFixture, config: dict[str, Path], error: bool, param_type_str: bool):
    opts = {"type": click.STRING} if param_type_str else {}
    expected_code = 0
    expected_output = ""

    if error:
        mocker.patch("clickext.decorators.Path.read_text", side_effect=OSError)
        expected_code = 1
        expected_output = "Error: Failed to read configuration file\n"

    @click.command(cls=ClickextCommand)
    @config_option(config["json_valid"], **opts)  # type:ignore
    def cmd(): ...

    runner = CliRunner()
    result = runner.invoke(cmd)

    assert result.exit_code == expected_code
    assert result.output == expected_output


@pytest.mark.parametrize("exists", [True, False])
@pytest.mark.parametrize("required", [True, False])
def test_config_option_file_required(config: dict[str, Path], required: bool, exists: bool):
    file = config["json_valid"] if exists else config["json_valid"] / "x"
    expected_code = 0
    expected_output = ""

    if required and not exists:
        expected_code = 1
        expected_output = "Error: Configuration file not found\n"

    @click.command(cls=ClickextCommand)
    @config_option(file, require_config=required)
    def cmd(): ...

    runner = CliRunner()
    result = runner.invoke(cmd)

    assert result.exit_code == expected_code
    assert result.output == expected_output


@pytest.mark.parametrize("param_decls", [tuple(), ("-o", "--override")])
def test_config_option_param_decls(config: dict[str, Path], param_decls: tuple[str, ...]):
    @click.command(cls=ClickextCommand)
    @config_option(config["json_invalid"], *param_decls)
    @click.pass_obj
    def cmd(obj: dict[str, str]):
        click.echo(obj)

    runner = CliRunner()
    result = runner.invoke(cmd, [param_decls[0] if param_decls else "-c", str(config["json_valid"])])

    assert result.exit_code == 0
    assert result.output == "{'key': 'default_value'}\n"


@pytest.mark.parametrize("valid", [True, False])
@pytest.mark.parametrize("config_format", ["ini", "json", "toml", "yaml"])
def test_config_option_parse(config: dict[str, Path], config_format: str, valid: bool):
    file = config[f"{config_format}_{'' if valid else 'in'}valid"]
    expected_code = 0
    expected_output = ""

    if config_format == "ini":
        expected_code = 1
        expected_output = 'Error: Unknown configuration file format ".ini"\n'
    elif not valid:
        expected_code = 1
        expected_output = "Error: Failed to parse configuration file\n"

    @click.command(cls=ClickextCommand)
    @config_option(file)
    def cmd(): ...

    runner = CliRunner()
    result = runner.invoke(cmd)

    assert result.exit_code == expected_code
    assert result.output == expected_output


@pytest.mark.parametrize("processor", [True, False])
def test_config_option_processor(config: dict[str, Path], processor: bool):
    def callback(data: dict[str, str]) -> dict[str, str]:
        data["key"] = "processed_value"
        return data

    @click.command(cls=ClickextCommand)
    @config_option(config["json_valid"], processor=callback if processor else None)
    @click.pass_obj
    def cmd(obj: dict[str, str]):
        click.echo(obj)

    runner = CliRunner()
    result = runner.invoke(cmd)

    assert result.exit_code == 0
    assert result.output == "{'key': '" + ("processed" if processor else "default") + "_value'}\n"


@pytest.mark.parametrize("verbose", [True, False])
def test_verbose_option_level(logger: logging.Logger, verbose: bool):
    @click.command(cls=ClickextCommand)
    @verbose_option(logger)
    def cmd():
        logger.debug("msg")
        logger.info("msg")

    runner = CliRunner()
    result = runner.invoke(cmd, "-v" if verbose else None)

    assert hasattr(logging, QUIET_LEVEL_NAME)  # test that `log.init_logging` was called
    assert logging.raiseExceptions is verbose
    assert logging.getLogger().level == (logging.DEBUG if verbose else logging.INFO)
    assert logger.level == logging.getLogger().level

    assert result.exit_code == 0
    assert result.output == "Debug: msg\nmsg\n" if verbose else "msg\n"


def test_verbose_option_root_handlers(logger: logging.Logger):
    @click.command(cls=ClickextCommand)
    @verbose_option(logger, root_handlers=[logging.NullHandler()])
    def cmd(): ...

    assert len(logging.getLogger().handlers) == 2
    assert isinstance(logging.getLogger().handlers[1], logging.NullHandler)


@pytest.mark.parametrize("param_decls", [tuple(), ("-o", "--override")])
def test_verbose_option_param_decls(logger: logging.Logger, param_decls: tuple[str, ...]):
    @click.command(cls=ClickextCommand)
    @verbose_option(logger, *param_decls)
    def cmd():
        logger.debug("msg")

    runner = CliRunner()
    result = runner.invoke(cmd, param_decls[0] if param_decls else "-v")

    assert result.exit_code == 0
    assert result.output == "Debug: msg\n"


def test_verbose_option_prefix_styles(logger: logging.Logger):
    @click.command(cls=ClickextCommand)
    @verbose_option(logger, prefix_styles={logging.INFO: {"fg": "red"}})
    def cmd(): ...

    runner = CliRunner()
    result = runner.invoke(cmd)

    assert result.exit_code == 0
    assert logging.getLogger().handlers[0].formatter.prefix_styles[logging.INFO] == {"fg": "red"}  # type: ignore


@pytest.mark.parametrize("default", [True, False])
def test_verbosity_option_default(logger: logging.Logger, default: bool):
    opts = {} if default else {"default": "ERROR"}

    @click.command(cls=ClickextCommand)
    @verbosity_option(logger, **opts)  # type: ignore
    def cmd():
        logger.info("msg")

    runner = CliRunner()
    result = runner.invoke(cmd)

    assert logging.getLogger().level == logging.INFO if default else logging.ERROR

    assert result.exit_code == 0
    assert result.output == ("msg\n" if default else "")


@pytest.mark.parametrize("level", [None, QUIET_LEVEL_NAME, "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "XYZ"])
def test_verbosity_option_level(logger: logging.Logger, level: t.Optional[str]):
    cmd_msg_level = logging.INFO
    expected_code = 0
    expected_output = "msg\n"

    if level == "XYZ":
        expected_code = 2
        expected_output = (
            "Usage: cmd [OPTIONS]\n"
            "Try 'cmd --help' for help.\n\n"
            "Error: Invalid value for '--verbosity' / '-v': "
            "'XYZ' is not one of 'QUIET', 'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'.\n"
        )
    elif level == QUIET_LEVEL_NAME:
        cmd_msg_level = QUIET_LEVEL_NUM
        expected_output = ""
    elif level is not None and level != "INFO":
        cmd_msg_level = logging.getLevelName(level)
        expected_output = f"{level.title()}: msg\n"

    @click.command(cls=ClickextCommand)
    @verbosity_option(logger)
    def cmd():
        logger.log(cmd_msg_level, "msg")

    runner = CliRunner()
    result = runner.invoke(cmd, [] if level is None else ["-v", level])

    assert hasattr(logging, QUIET_LEVEL_NAME)  # test that `log.init_logging` was called
    assert logging.raiseExceptions is (level == "DEBUG")
    assert logging.getLogger().level == cmd_msg_level
    assert logger.level == logging.getLogger().level

    assert result.exit_code == expected_code
    assert result.output == expected_output


@pytest.mark.parametrize("level", ["DEBUG", "debug"])
def test_verbosity_option_level_case_insensitive(logger: logging.Logger, level: str):
    @click.command(cls=ClickextCommand)
    @verbosity_option(logger)
    def cmd():
        logger.debug("msg")

    runner = CliRunner()
    result = runner.invoke(cmd, ["-v", level])

    assert result.exit_code == 0
    assert result.output == "Debug: msg\n"


@pytest.mark.parametrize("param_decls", [tuple(), ("-o", "--override")])
def test_verbosity_option_param_decls(logger: logging.Logger, param_decls: tuple[str, ...]):
    @click.command(cls=ClickextCommand)
    @verbosity_option(logger, *param_decls)
    def cmd():
        logger.debug("msg")

    runner = CliRunner()
    result = runner.invoke(cmd, [param_decls[0] if param_decls else "-v", "DEBUG"])

    assert result.exit_code == 0
    assert result.output == "Debug: msg\n"


def test_verbosity_option_prefix_styles(logger: logging.Logger):
    @click.command(cls=ClickextCommand)
    @verbosity_option(logger, prefix_styles={logging.INFO: {"fg": "red"}})
    def cmd(): ...

    runner = CliRunner()
    result = runner.invoke(cmd)

    assert result.exit_code == 0
    assert logging.getLogger().handlers[0].formatter.prefix_styles[logging.INFO] == {"fg": "red"}  # type: ignore


def test_verbosity_option_root_handlers(logger: logging.Logger):
    @click.command(cls=ClickextCommand)
    @verbosity_option(logger, root_handlers=[logging.NullHandler()])
    def cmd(): ...

    assert len(logging.getLogger().handlers) == 2
    assert isinstance(logging.getLogger().handlers[1], logging.NullHandler)
