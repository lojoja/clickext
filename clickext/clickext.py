"""
clickext

Extended features for the click library.
"""

import logging
from typing import Any

import click


__all__ = [
    "AliasCommand",
    "AliasAwareGroup",
    "CommonOptionGroup",
    "DebugCommonOptionGroup",
]


class Formatter(logging.Formatter):
    """Format click log messages

    Messages are prefixed with the log level. The log level is colored in console output.

    Attributes:
        colors: A `dict` mapping log levels to their display color.
    """

    colors = {
        "critical": "red",
        "debug": "blue",
        "error": "red",
        "warning": "yellow",
    }

    def format(self, record):
        if not record.exc_info:
            level = record.levelname.lower()
            msg = record.msg

            if level in self.colors:
                prefix = click.style(f"{level.title()}: ", fg=self.colors[level])

                if not isinstance(msg, str):
                    msg = str(msg)

                msg = "\n".join(f"{prefix}{line}" for line in msg.splitlines())

            return msg

        return logging.Formatter.format(self, record)


class Handler(logging.Handler):
    """Handle click log messages

    Messages are handled with `click.echo` if possible, otherwise falling back to the default handler.

    Attributes:
        error_levels: A `list` of log levels that should be considered errors.
    """

    error_levels = ["critical", "error", "warning"]

    def emit(self, record):
        try:
            msg = self.format(record)
            err = record.levelname.lower() in self.error_levels
            click.echo(msg, err=err)
        except Exception:  # pylint: disable=broad-except
            self.handleError(record)


logger = logging.getLogger()

clickext_handler = Handler()
clickext_handler.setFormatter(Formatter())
logger.addHandler(clickext_handler)

click.ClickException.show = lambda self, file=None: logger.error(self.message)
click.UsageError.show = lambda self, file=None: logger.error(self.format_message())


class AliasCommand(click.Command):
    """A command with one or more aliases.

    Command aliases offer an alternate, typically shorter, command name for a simpler cli interface.
    Aliased commands must be defined in a `AliasAwareGroup`. Aliases are specified as arguments in the command
    definition decorator.

    ```
    import click
    import clickext

    @click.group(cls=AliasAwareGroup)
    def cli():
        ...

    @cli.command(cls=AliasCommand, aliases=['foo'])
    def foobar():
        ...
    ```

    Arguments:
        aliases: A `list` of `str` aliases for the command.
    """

    def __init__(self, aliases: list[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aliases = sorted(aliases)

    @property
    def name_for_help(self) -> str | None:
        """Show alias names in command help"""
        if self.aliases:
            return f'{self.name} ({",".join(self.aliases)})'
        return self.name


class AliasAwareGroup(click.Group):
    """A command group that handles aliased and non-aliased commands.

    ```
    import click
    import clickext

    @click.group(cls=AliasAwareGroup)
    def cli():
        ...

    @cli.command(cls=AliasCommand, aliases=['cmd'])
    def command_one():
        ...

    @cli.command()
    def command_two():
        ...
    ```

    """

    def get_command(self, ctx, cmd_name):
        """Check for and resolve aliased command names and return the command."""
        if cmd_name not in self.commands:
            for name, cmd in self.commands.items():
                if isinstance(cmd, AliasCommand) and cmd_name in getattr(cmd, "aliases", []):
                    cmd_name = name
                    break
        return super().get_command(ctx, cmd_name)

    def format_commands(self, ctx, formatter):
        rows = []
        limit = formatter.width - 6 - len(max(self.commands))

        for name, cmd in self.commands.items():
            if cmd is None or cmd.hidden:
                continue

            name = getattr(cmd, "name_for_help", name)
            cmd_help = cmd.get_short_help_str(limit)
            rows.append((name, cmd_help))

        if rows:
            with formatter.section("Commands"):
                formatter.write_dl(rows)


class CommonOptionGroup(AliasAwareGroup):
    """An alias-aware command group that adds common options to all commands.

    Common options are specified as arguments in the command group definition decorator. The `pre_invoke_hook` method
    can be called to do any pre-processing or configuration based on the values of the common options before the command
    is invoked.

    ```
    @click.group(cls=CommonOptionGroup, common_options=[
            'foo': click.Option(["--foo", "-f"], is_flag=True),
            'bar': click.Option(["--bar", "-b"], is_flag=True)
        ]
    )
    def cli():
        ...

    @cli.command()
    @cli.Option('--baz', is_flag=True)
    def command(foo, bar, baz):
        ...
    ```

    Arguments:
        common_options = A `list` of `click.Option` objects
    """

    def __init__(self, common_options: list[click.Option], *args, **kwargs):
        self.common_options = common_options
        super().__init__(*args, **kwargs)

    def add_command(self, cmd, name=None):
        """Attach common options to the command, sort by name, and register with the command group."""
        cmd.params.extend(self.common_options)
        cmd.params.sort(key=lambda x: x.opts[0])
        super().add_command(cmd, name)

    def invoke(self, ctx):
        """Set the common option flag values and invoke the command."""
        option_values: dict[str, Any] = {}

        for option in self.common_options:
            option_values[option.name] = (  # type: ignore
                option.flag_value if any(arg in option.opts for arg in ctx.args) else option.default
            )

        self.pre_invoke_hook(option_values, ctx)
        super().invoke(ctx)

    def pre_invoke_hook(self, option_values: dict[str, Any], ctx: click.Context) -> None:
        """Process common option flags before invoking the command.

        Arguments:
            option_values: A `dict` of resolved common option flag values keyed by the option name.
            ctx: The current context.
        """


class DebugCommonOptionGroup(CommonOptionGroup):
    """A `CommonOptionGroup` that adds a debug option flag to all commands.

    The debug flag sets the verbosity level of the logger. When passed, debug statements will be output on the console,
    otherwise only messages of `logging.INFO` or higher will be output.

    ```
    @click.group(cls=DebugCommonOptionGroup)
    def cli():
        ...

    @cli.command()
    @cli.option('--bar', is_flag=True)
    def command(bar, debug):
        ...
    ```

    """

    def __init__(self, *args, **kwargs):
        common_options = kwargs.pop("common_options", [])
        common_options.append(
            click.Option(
                param_decls=["--debug"],
                is_flag=True,
                default=False,
                help="Show debug statements.",
            )
        )
        super().__init__(common_options, *args, **kwargs)

    def pre_invoke_hook(self, option_values, ctx):
        logger.setLevel(logging.DEBUG if option_values["debug"] else logging.INFO)
        super().pre_invoke_hook(option_values, ctx)
