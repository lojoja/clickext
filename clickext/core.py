"""
clickext.core

Extended functionality for the click library.
"""

import typing as t

import click


__all__ = [
    "ClickextCommand",
    "ClickextGroup",
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
        group_opts: Internal storage of global group options that are not parsed with the command arguments.
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
        self.group_opts: list[click.Option] = []

        super().__init__(*args, **kwargs)

    def invoke(self, ctx):
        """Given a context, this invokes the command.

        Mutually exclusive options are validated before invoking the command. Uncaught non-click exceptions
        (excluding `EOFError`, `KeyboardInterrupt`, and `OSError`) are caught and re-raised as a `click.ClickException`
        to prevent stack traces and other undesireable output leaking to the console.

        Raises:
            click.clickException: When an uncaught exception occurs during invocation.
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

    def format_options(self, ctx, formatter):
        """Add options to the program help display.

        Options are sorted alphabetically by the first CLI option string. If this command is part of a `ClickextGroup`
        global group options are included in the option display.
        """
        params = [*self.get_params(ctx), *self.group_opts]
        params.sort(key=lambda x: x.opts[0])

        opts = []

        for param in params:
            record = param.get_help_record(ctx)
            if record is not None:
                opts.append(record)

        if opts:
            with formatter.section("Options"):
                formatter.write_dl(opts)

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


class ClickextGroup(click.Group):
    """A clickext command group.

    Clickext command groups require `ClickextCommand` command instances, and support aliases and global options.

    Global options are options defined at the group level that may be passed as arguments to the group command
    and all subcommands in the group. Typically these options are used to change configuration or execution globally
    (e.g., to set verbosity level). Global options are extracted and prepended to the arguments prior to argument
    parsing; they are not passed to subcommands and must not be part of a subcommand function signature.

    Global option names cannot be the same as a subcommand name, subcommand option name, or share long/short option
    strings with a subcommand option. Additionally, non-flag global options should not accept values that begin with "-"
    or values identical to a subcommand name.

    Attributes:
        global_opts: A `list` of group option names that can be passed to any command in the group.

    Raises:
        ValueError: When a named global option does not exist.
        TypeError: When a named global option is not a `click.Option`.
    """

    def __init__(
        self,
        *args,
        global_opts: t.Optional[list[str]] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        global_opts = global_opts or []

        for name in global_opts:
            param = next((p for p in self.params if p.name == name), None)

            if not param:
                raise ValueError(f"Unknown global option {name}")

            if not isinstance(param, click.Option):
                raise TypeError(f"Invalid global option {name}; global options must be a 'click.Option'")

        self.global_opts = global_opts

    def invoke(self, ctx):
        """Given a context, this invokes the command.

        Uncaught non-click exceptions (excluding `EOFError`, `KeyboardInterrupt`, and `OSError`) are caught and
        re-raised as a `click.ClickException` to prevent stack traces and other undesireable output leaking to the
        console.

        Raises:
            click.clickException: When an uncaught exception occurs during invocation.
        """
        try:
            return super().invoke(ctx)
        except (EOFError, KeyboardInterrupt, OSError, click.Abort, click.ClickException, click.exceptions.Exit):
            raise
        except Exception as exc:  # pylint: disable=broad-except
            raise click.ClickException(str(exc)) from exc

    def parse_args(self, ctx, args):
        """Parse arguments and update the context.

        Global options are extracted and prepended to the argument list before parsing.
        """
        grp_args: list[str] = []
        cmd_args: list[str] = []

        next_idx = 0
        for idx, arg in enumerate(args):
            # skip arguments consumed as values for a global option
            if idx != next_idx:
                continue

            gopt = next((go for go in self.get_global_options() if arg in go.opts), None)

            if gopt:
                grp_args.append(arg)

                value_idx = idx + 1
                if not gopt.is_flag and value_idx < len(args):
                    if not args[value_idx].startswith("-") and args[value_idx] not in self.commands:
                        grp_args.append(args[value_idx])
                        next_idx += 1
            else:
                cmd_args.append(arg)

            next_idx += 1

        args = [*grp_args, *cmd_args]
        return super().parse_args(ctx, args)

    def get_global_options(self) -> list[click.Option]:
        """Get the global group option parameters."""
        return [param for param in self.params if param.name in self.global_opts]  #  type:ignore

    def add_command(self, cmd: ClickextCommand, name=None):
        """Register a command with this group.

        Command and command options are validated against global options before registration. Global options are stored
        separately on the command to use in the program help display.

        Raises:
            TypeError: When a command that is not a `ClickextCommand` is added to the group.
            ValueError: When the command name is the same as a global option name; a command option has the same name as
                        a global option, or a command option has the same long/short option string as a global option.
        """
        if not isinstance(cmd, ClickextCommand):
            raise TypeError("Only 'ClickextCommand's can be registered with a 'ClickextGroup'")

        name = name or cmd.name

        if name is not None:
            if name in self.global_opts:
                raise ValueError(f"Subcommand {name} conflicts with a global option name")

            for param in cmd.params:
                if param.name in self.global_opts:
                    raise ValueError(f"Subcommand option {param.name} conflicts with a global option name")

                for opt in param.opts:
                    if any(opt in gopt.opts for gopt in self.get_global_options()):
                        raise ValueError(f"Subcommand option string {opt} conflicts with a global option string")

            cmd.group_opts = self.get_global_options()

        super().add_command(cmd, name)

    def get_command(self, ctx, cmd_name):
        """Get a command by name or alias."""
        for name, cmd in self.commands.items():
            if cmd_name == name or cmd_name in getattr(cmd, "aliases", []):
                cmd_name = name
                break

        return super().get_command(ctx, cmd_name)

    def format_commands(self, ctx, formatter):
        """Add subcommands to the program help display."""

        commands: list[tuple[str, click.Command]] = []

        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)

            if cmd is None or cmd.hidden:
                continue

            aliases = getattr(cmd, "aliases", [])

            if aliases:
                subcommand = f"{subcommand} ({','.join(aliases)})"

            commands.append((subcommand, cmd))

        # allow for 3 times the default spacing
        if commands:
            limit = formatter.width - 6 - max(len(cmd[0]) for cmd in commands)
            rows = []

            for subcommand, cmd in commands:
                cmd_help = cmd.get_short_help_str(limit)
                rows.append((subcommand, cmd_help))

            if rows:
                with formatter.section("Commands"):
                    formatter.write_dl(rows)

    def format_options(self, ctx, formatter):
        """Add options to the program help display.

        Options are sorted alphabetically by the first CLI option string.
        """
        params = self.get_params(ctx)
        params.sort(key=lambda x: x.opts[0])

        opts = []

        for param in params:
            record = param.get_help_record(ctx)
            if record is not None:
                opts.append(record)

        if opts:
            with formatter.section("Options"):
                formatter.write_dl(opts)

        self.format_commands(ctx, formatter)
