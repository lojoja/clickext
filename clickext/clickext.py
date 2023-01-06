"""
clickext.clickext

Extended functionality for the click library.
"""

import typing as t

import click


__all__ = [
    "ClickextCommand",
    "AliasAwareGroup",
    "CommonOptionGroup",
    "DebugCommonOptionGroup",
]


class ClickextCommand(click.Command):
    """A clickext command.

    Clickext commands support aliases and marking options as mutually exclusive.

    Aliases have no effect unless the command is a subcommand in a `ClickextGroup`.

    Mutually exclusive options are validated before invoking the command, and will fail validation when all mutually
    exclusive options were passed as arguments and one or more options has a value other than its default.

    Attributes:
        aliases: Alternate names that should invoke this command.
        mx_opts: Groups of options that are mutually exclusive. Each item in the list is a `tuple` of `click.Option`
                 names that cannot be used together.
    """

    def __init__(
        self,
        *args,
        aliases: t.Optional[list[str]] = None,
        mx_opts: t.Optional[list[tuple[str]]] = None,
        **kwargs,
    ):
        self.aliases = sorted(aliases or [])
        self.mx_opts = mx_opts or []

        super().__init__(*args, **kwargs)

    def invoke(self, ctx):
        """Given a context, this invokes the command.

        Mutually exclusive options are validated before invoking the command. Uncaught non-click exceptions
        (excluding `EOFError`, `KeyboardInterrupt`, and `OSError`) are caught and re-raised as a `click.ClickException`
        to prevent stack traces and other undesireable output leaking to the console.

        Raises:
            click.UsageError: When mutually exclusive options have been passed.
        """
        for ex_opts in self.mx_opts:
            passed = []

            for param in self.get_params(ctx):
                if param.name in ex_opts and param.name in ctx.params and ctx.params[param.name] != param.default:
                    passed.append(param.opts[0])

                    if len(passed) == len(ex_opts):
                        raise click.UsageError(f"Mutually exclusive options: {' '.join(passed)}", ctx)

        try:
            return super().invoke(ctx)
        except (EOFError, KeyboardInterrupt, OSError, click.Abort, click.ClickException, click.exceptions.Exit):
            raise
        except Exception as exc:  # pylint: disable=broad-except
            raise click.ClickException(str(exc)) from exc

    def format_help(self, ctx, formatter):
        """Writes the help into the formatter if it exists."""
        super().format_help(ctx, formatter)
        self.format_aliases(ctx, formatter)

        if self.aliases:
            return f'{self.name} ({",".join(self.aliases)})'
        return self.name


    def format_aliases(self, ctx: click.Context, formatter: click.HelpFormatter):  # pylint: disable=unused-argument
        """Add aliases to the program help display when command is a subcommand."""
        if ctx.parent:
            aliases = []

            if self.aliases:
                for alias in self.aliases:
                    aliases.append((alias, ""))

            if aliases:
                with formatter.section("Aliases"):
                    formatter.write_dl(aliases)

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
