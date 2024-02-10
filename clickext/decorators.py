"""
clickext.decorators

Argument and option decorators for clickext commands.
"""

import json
import logging
from pathlib import Path
import typing as t

import click
import tomli
import yaml

try:
    from yaml import CLoader as YamlLoader
except ImportError:  # pragma: no cover
    from yaml import Loader as YamlLoader

from .core import ClickextCommand


_AnyCallable: t.TypeAlias = t.Callable[..., t.Any]
FC = t.TypeVar("FC", bound=_AnyCallable | ClickextCommand)


def config_option(
    file: Path | str,
    *param_decls: str,
    processor: t.Optional[_AnyCallable] = None,
    require_config: bool = False,
    **kwargs: t.Any,
) -> t.Callable[[FC], FC]:
    """Adds a configuration file option.

    Provides a method to load, parse, and optionally prepare data from a configuration file. The result is saved to
    `ctx.obj` and can be accessed with `@click.pass_context`, `@click.pass_obj`, or by registering a
    `click.make_pass_decorator` for the prepared data object type. This option is non-eager so the configuration is not
    loaded when the program will not run (for example, when "--help" or "--version" is passed).

    Configuration files must be a JSON, TOML, or YAML file. The file extension determines the file format:

    JSON:

        - .json

    TOML:

        - .toml

    YAML:

        - .yaml
        - .yml

    The config option itself is always optional, however setting `require_config` to `True` will prevent the program
    starting if a configuration file is not present. If a configuration file is missing, is not required, and a
    `processor` is specified, the processor will be passed the `None` value for program-specific handling, otherwise
    `ctx.obj` will be set to `None`.

    Arguments:
        file: The default configuration file location.
        param_decls: One or more option names. Defaults to "--config / -c".
        processor: An optional callable that receives the parsed data and prepares it per the program's specifications.
                   This callable must accept a `None` value and return the prepared data or object.
        require_config: Whether a configuration file is required to start the program.

    Raises:
        click.ClickException: When the configuration file 1) is required and doesn't exist, 2) cannot be read,
                              3) cannot be parsed, or 4) is an unknown format.
    """

    def callback(
        ctx: click.Context, param: click.Parameter, value: Path | str  # pylint: disable=unused-argument
    ) -> None:
        if isinstance(value, str):
            value = Path(value)

        raw_text = None

        if value.is_file():
            try:
                raw_text = value.read_text(encoding="utf8")
            except IOError as exc:
                raise click.ClickException("Failed to read configuration file") from exc
        elif require_config:
            raise click.ClickException("Configuration file not found")

        if raw_text:
            try:
                match value.suffix:
                    case ".json":
                        config = json.loads(raw_text)
                    case ".toml":
                        config = tomli.loads(raw_text)
                    case ".yaml" | ".yml":
                        config = yaml.load(raw_text, Loader=YamlLoader)
                    case _:
                        raise click.ClickException(f'Unknown configuration file format "{value.suffix}"')
            except (json.JSONDecodeError, tomli.TOMLDecodeError, yaml.YAMLError) as exc:
                raise click.ClickException("Failed to parse configuration file") from exc
        else:
            config = None

        if processor:
            config = processor(config)

        ctx.obj = config

    if not param_decls:
        param_decls = ("--config", "-c")

    kwargs.setdefault("expose_value", False)
    kwargs.setdefault("help", "The configuration file to use")
    kwargs["default"] = str(file)
    kwargs["is_eager"] = False
    kwargs["callback"] = callback
    kwargs["required"] = False

    return click.option(*param_decls, **kwargs)


def verbose_option(logger: logging.Logger, *param_decls: str, **kwargs: t.Any) -> t.Callable[[FC], FC]:
    """Adds a verbose option.

    A flag to switch between standard output and verbose output. Output is handled by the given logger. The logger must
    be passed to `clickext.init_logging` before using the decorator.

    Arguments:
        logger: The logger instance to modify.
        param_decls: One or more option names. Defaults to "--verbose / -v".
        kwargs: Extra arguments passed to `click.option`.
    """

    def callback(ctx: click.Context, param: click.Parameter, value: bool) -> None:  # pylint: disable=unused-argument
        level = logging.DEBUG if value else logging.INFO
        logger.setLevel(level)

    if not param_decls:
        param_decls = ("--verbose", "-v")

    kwargs.setdefault("metavar", "LVL")
    kwargs.setdefault("expose_value", False)
    kwargs.setdefault("help", "Increase verbosity")
    kwargs["is_flag"] = True
    kwargs["flag_value"] = True
    kwargs["default"] = False
    kwargs["is_eager"] = True
    kwargs["callback"] = callback

    return click.option(*param_decls, **kwargs)


def verbosity_option(logger: logging.Logger, *param_decls: str, **kwargs: t.Any) -> t.Callable[[FC], FC]:
    """Adds a configurable verbosity option.

    Output is handled by the given logger. The logger must be passed to `clickext.init_logging` before using the
    decorator. Available verbosity levels are (from least to most verbose):

        - "QUIET"
        - "CRITICAL"
        - "ERROR"
        - "WARNING"
        - "INFO" (DEFAULT)
        - "DEBUG"

    Levels are case-insensitive.

    Arguments:
        logger: The logger instance to modify.
        param_decls: One or more option names. Defaults to "--verbosity / -v".
        kwargs: Extra arguments passed to `click.option`.
    """

    def callback(ctx: click.Context, param: click.Parameter, value: str) -> None:  # pylint: disable=unused-argument
        logger.setLevel(getattr(logging, value.upper()))

    if not param_decls:
        param_decls = ("--verbosity", "-v")

    kwargs.setdefault("default", "INFO")
    kwargs.setdefault("metavar", "LVL")
    kwargs.setdefault("expose_value", False)
    kwargs.setdefault("help", "Specify verbosity level")
    kwargs["is_eager"] = True
    kwargs["type"] = click.Choice(["QUIET", "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"], case_sensitive=False)
    kwargs["callback"] = callback

    return click.option(*param_decls, **kwargs)
