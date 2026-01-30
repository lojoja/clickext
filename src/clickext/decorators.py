"""
clickext.decorators

Argument and option decorators for clickext commands.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import typing as t

import click
import tomli
import yaml

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:  # pragma: no cover
    from yaml import SafeLoader

from .core import ClickextCommand
from .log import init_logging

if t.TYPE_CHECKING:
    from .log import Styles


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

        - JSON:

            - .json

        - TOML:

            - .toml

        - YAML:

            - .yaml
            - .yml

    The config option itself is always optional, however setting `require_config` to `True` will prevent the program
    starting if a configuration file is not present. If a configuration file is missing, is not required, and a
    `processor` is specified, the processor will be passed the `None` value for program-specific handling, otherwise
    `ctx.obj` will be set to `None`.

    By default this option uses the `click.Path` parameter type and returns a `pathlib.Path` object to the loader
    callback. It will also accept a `str` via the `click.STRING` parameter type if the program cannot use `click.Path`
    for some reason.

    :param file: The default configuration file location.
    :param param_decls: One or more option names. (Default: "--config / -c").
    :param processor: An optional callable that receives the parsed config file and prepares it per the program's
    specifications. This callable must accept a `None` value and return the prepared data or object.
    :param require_config: Whether a configuration file is required to start the program.

    :raises click.ClickException: When the configuration file 1) is required and doesn't exist, 2) cannot be read,
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
            except OSError as exc:
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
                        config = yaml.load(raw_text, Loader=SafeLoader)
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
    kwargs.setdefault("help", "The configuration file to use.")
    kwargs.setdefault("type", click.Path(path_type=Path))
    kwargs["default"] = str(file)
    kwargs["is_eager"] = False
    kwargs["callback"] = callback
    kwargs["required"] = False

    return click.option(*param_decls, **kwargs)


def verbose_option(
    logger: logging.Logger,
    *param_decls: str,
    root_handlers: t.Optional[list[logging.Handler]] = None,
    prefix_styles: t.Optional[dict[int, t.Optional[Styles]]] = None,
    **kwargs: t.Any,
) -> t.Callable[[FC], FC]:
    """Adds a verbose option.

    A flag to switch between standard output and verbose output. The `--verbose` flag should be passed before any other
    eager options to ensure the desired verbosity level is set before the other options are evaluated. This option
    initializes the logging environment so it is not necessary to call `log.init_logging` when this option is used.

    :param logger: The program logger. Required to initialize logging. See `clickext.log.init_logging`.
    :param param_decls: One or more option names. (Default: "--verbose / -v").
    :param root_handlers: Additional handlers to attach to the root logger. See `clickext.log.init_logging`.
    :param prefix_styles: Log level prefix display styles. See: `clickext.log.ConsoleFormatter` for format.
    :param kwargs: Extra arguments passed to `click.option`.
    """

    def callback(ctx: click.Context, param: click.Parameter, value: bool) -> None:  # pylint: disable=unused-argument
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG if value else logging.INFO)
        logger.setLevel(root_logger.level)
        logging.raiseExceptions = root_logger.level == logging.DEBUG

    init_logging(logger, root_handlers=root_handlers, prefix_styles=prefix_styles)

    if not param_decls:
        param_decls = ("--verbose", "-v")

    kwargs.setdefault("metavar", "LVL")
    kwargs.setdefault("expose_value", False)
    kwargs.setdefault("help", "Increase verbosity.")
    kwargs["is_flag"] = True
    kwargs["flag_value"] = True
    kwargs["default"] = False
    kwargs["is_eager"] = True
    kwargs["callback"] = callback

    return click.option(*param_decls, **kwargs)


def verbosity_option(
    logger: logging.Logger,
    *param_decls: str,
    root_handlers: t.Optional[list[logging.Handler]] = None,
    prefix_styles: t.Optional[dict[int, t.Optional[Styles]]] = None,
    **kwargs: t.Any,
) -> t.Callable[[FC], FC]:
    """Adds a configurable verbosity option.

    The `--verbosity` flag should be passed before any other eager options to ensure the desired verbosity level is set
    before the other options are evaluated. This option initializes the logging environment so it is not necessary to
    call `log.init_logging` when this option is used. Available verbosity levels are (from least to most verbose):

        - "QUIET"
        - "CRITICAL"
        - "ERROR"
        - "WARNING"
        - "INFO" (DEFAULT)
        - "DEBUG"

    Levels are case-insensitive.

    :param logger: The program logger. Required to initialize logging. See `clickext.log.init_logging`.
    :param param_decls: One or more option names. (Default: "--verbosity / -v").
    :param root_handlers: Additional handlers to attach to the root logger. See `clickext.log.init_logging`.
    :param prefix_styles: Log level prefix display styles. See: `clickext.log.ConsoleFormatter` for format.
    :param kwargs: Extra arguments passed to `click.option`.
    """

    def callback(ctx: click.Context, param: click.Parameter, value: str) -> None:  # pylint: disable=unused-argument
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, value.upper()))
        logger.setLevel(root_logger.level)
        logging.raiseExceptions = logger.getEffectiveLevel() == logging.DEBUG

    init_logging(logger, level=kwargs.get("default", "INFO"), root_handlers=root_handlers, prefix_styles=prefix_styles)

    if not param_decls:
        param_decls = ("--verbosity", "-v")

    kwargs.setdefault("default", "INFO")
    kwargs.setdefault("metavar", "LVL")
    kwargs.setdefault("expose_value", False)
    kwargs.setdefault("help", "Specify verbosity level.")
    kwargs["is_eager"] = True
    kwargs["type"] = click.Choice(["QUIET", "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"], case_sensitive=False)
    kwargs["callback"] = callback

    return click.option(*param_decls, **kwargs)
