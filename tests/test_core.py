# pylint: disable=missing-module-docstring,missing-function-docstring,unused-argument

from contextlib import nullcontext as does_not_raise
import typing as t

import click
from click.testing import CliRunner
import pytest

from clickext.core import ClickextCommand, ClickextGroup


@pytest.mark.parametrize("aliases", [None, [], ["b", "a", "c"]])
def test_clickext_command_aliases(aliases: t.Optional[list[str]]):
    cmd = ClickextCommand(aliases=aliases)
    assert cmd.aliases == (sorted(aliases) if aliases else [])


def test_clickext_command_global_options():
    cmd = ClickextCommand()
    assert cmd.global_opts == {}  # pylint: disable=use-implicit-booleaness-not-comparison


def test_clickext_command_help():
    @click.command(cls=ClickextCommand, aliases=["a", "b"])
    @click.option("--opt", hidden=True)
    def cmd(opt: str): ...

    runner = CliRunner()
    result = runner.invoke(cmd, "--help")

    assert result.exit_code == 0
    assert result.output == "Usage: cmd [OPTIONS]\n\nOptions:\n  --help  Show this message and exit.\n"


@pytest.mark.parametrize("opt2", ["", "--opt2"])
@pytest.mark.parametrize("opt1", ["", "--opt1"])
@pytest.mark.parametrize("mx_opts", [[], [("opt1", "opt2")]])
def test_clickext_command_validate_mutually_exclusive_options(mx_opts: list[tuple[str]], opt1: str, opt2: str):
    @click.command(cls=ClickextCommand, mx_opts=mx_opts)
    @click.option("--opt1", is_flag=True, default=False)
    @click.option("--opt2", is_flag=True, default=False)
    def cmd(opt1: bool, opt2: bool): ...

    runner = CliRunner()
    result = runner.invoke(cmd, " ".join([opt1, opt2]))

    if mx_opts and opt1 and opt2:
        assert result.exit_code == 2
        assert result.output == (
            "Usage: cmd [OPTIONS]\n"
            "Try 'cmd --help' for help.\n\n"
            "Error: Mutually exclusive options: --opt1 --opt2\n"
        )
    else:
        assert result.exit_code == 0
        assert result.output == ""


@pytest.mark.parametrize("cmd_name", ["cmd", "a", "undefined"])
def test_clickext_group_command_aliases(cmd_name: str):
    expected_code = 0
    expected_output = ""

    if cmd_name == "undefined":
        expected_code = 2
        expected_output = (
            "Usage: grp [OPTIONS] COMMAND [ARGS]...\n"
            "Try 'grp --help' for help.\n\nError: No such command 'undefined'.\n"
        )

    @click.group(cls=ClickextGroup)
    def grp(): ...

    @grp.command(cls=ClickextCommand, aliases=["a"])
    def cmd(): ...

    runner = CliRunner()
    result = runner.invoke(grp, cmd_name)

    assert result.exit_code == expected_code
    assert result.output == expected_output


@pytest.mark.parametrize("cmd_class", [click.Command, ClickextCommand])
def test_clickext_group_command_class(cmd_class: click.Command):
    context = does_not_raise()

    if cmd_class is click.Command:
        context = pytest.raises(TypeError, match="Only 'ClickextCommand's can be registered with a 'ClickextGroup'")

    with context:

        @click.group(cls=ClickextGroup)
        def grp(): ...

        @grp.command(cls=cmd_class)
        def cmd(): ...


@pytest.mark.parametrize("with_cmds", [True, False])
def test_clickext_group_help(with_cmds: bool):
    command_section = ""

    @click.group(cls=ClickextGroup, global_opts=["opt1"], shared_params=["opt2"])
    @click.option("--opt1")
    @click.option("--opt2")
    def grp(opt1: str): ...

    if with_cmds:
        command_section = "\nCommands:\n  cmd1 (a,b)\n  cmd2\n"

        @grp.command(cls=ClickextCommand, aliases=["a", "b"])
        def cmd1(opt1: str, opt2: str): ...

        @grp.command(cls=ClickextCommand)
        def cmd2(opt1: str, opt2: str): ...

        @grp.command(cls=ClickextCommand, hidden=True)
        def cmd3(opt1: str, opt2: str): ...

    runner = CliRunner()
    result = runner.invoke(grp, "--help")

    assert result.exit_code == 0
    assert result.output == (
        "Usage: grp [OPTIONS] COMMAND [ARGS]...\n\n"
        "Options:\n"
        "  --help       Show this message and exit.\n"
        "  --opt1 TEXT\n"
        f"{command_section}"
    )


@pytest.mark.parametrize("cmd", ["cmd1", "cmd2"])
def test_clickext_group_help_subcommand(cmd: str):
    alias_section = "\nAliases:\n  a\n  b\n" if cmd == "cmd1" else ""

    @click.group(cls=ClickextGroup, global_opts=["opt1"], shared_params=["opt2"])
    @click.option("--opt1")
    @click.option("--opt2")
    def grp(opt1: str): ...

    @grp.command(cls=ClickextCommand, aliases=["a", "b"])
    def cmd1(opt1: str, opt2: str): ...

    @grp.command(cls=ClickextCommand)
    def cmd2(opt1: str, opt2: str): ...

    runner = CliRunner()
    result = runner.invoke(grp, [cmd, "--help"])

    assert result.exit_code == 0
    assert result.output == (
        f"Usage: grp {cmd} [OPTIONS]\n\n"
        "Options:\n"
        "  --help       Show this message and exit.\n"
        "  --opt1 TEXT\n"
        "  --opt2 TEXT\n"
        f"{alias_section}"
    )


@pytest.mark.parametrize("global_opts", [None, [], ["opt"], ["arg"], ["undefined"]])
def test_clickext_group_global_options_init(global_opts: t.Optional[list[str]]):
    context = does_not_raise()

    if global_opts:
        if "undefined" in global_opts:
            context = pytest.raises(ValueError, match="Unknown global option undefined")
        elif "arg" in global_opts:
            context = pytest.raises(
                TypeError, match="Invalid global option arg; global options must be a 'click.Option'"
            )

    with context:

        @click.group(cls=ClickextGroup, global_opts=global_opts)
        @click.argument("arg")
        @click.option("--opt")
        def grp(): ...


@pytest.mark.parametrize("extra_opt", ["--extra-opt", "-e"])
@pytest.mark.parametrize("opt", ["--opt", "-o"])
@pytest.mark.parametrize(
    "args_template",
    [
        "{opt} cmd",
        "{opt} cmd {extra_opt}",
        "{opt} {extra_opt} cmd",
        "{opt} {extra_opt} cmd {extra_opt}",
        "{extra_opt} cmd {opt}",
        "{extra_opt} cmd {opt} {extra_opt}",
        "{extra_opt} cmd {extra_opt} {opt}",
        "{extra_opt} {opt} cmd",
        "{extra_opt} {opt} cmd {extra_opt}",
    ],
)
def test_clickext_group_global_options_parse_flag(args_template: str, opt: str, extra_opt: str):
    @click.group(cls=ClickextGroup, global_opts=["opt"])
    @click.option("--opt", "-o", is_flag=True)
    @click.option("--extra-opt", "-e", is_flag=True)
    def grp(opt: bool, extra_opt: bool): ...

    @grp.command(cls=ClickextCommand)
    @click.option("--extra-opt", "-e", is_flag=True)
    def cmd(extra_opt: bool): ...

    runner = CliRunner()
    result = runner.invoke(grp, args_template.format(opt=opt, extra_opt=extra_opt))

    assert result.exit_code == 0
    assert result.output == ""


@pytest.mark.parametrize("extra_opt", ["--extra-opt", "-e"])
@pytest.mark.parametrize("opt", ["--opt", "-o"])
@pytest.mark.parametrize(
    ["args_template", "should_fail"],
    [
        ("{opt} cmd", True),
        ("{opt} cmd {extra_opt}", True),
        ("{opt} {extra_opt} cmd", False),
        ("{opt} {extra_opt} cmd {extra_opt}", False),
        ("{opt} val cmd", False),
        ("{opt} val cmd {extra_opt}", False),
        ("{opt} val {extra_opt} cmd", False),
        ("{opt} val {extra_opt} cmd {extra_opt}", False),
        ("cmd {opt}", True),
        ("cmd {opt} val", False),
        ("cmd {opt} val {extra_opt}", False),
        ("cmd {opt} {extra_opt}", True),
    ],
)
def test_clickext_group_global_options_parse_value(args_template: str, should_fail: bool, opt: str, extra_opt: str):
    expected_code = 0
    expected_output = ""

    if should_fail:
        expected_code = 2
        expected_output = (
            "Usage: grp [OPTIONS] COMMAND [ARGS]...\nTry 'grp --help' for help.\n\nError: Missing command.\n"
        )

    @click.group(cls=ClickextGroup, global_opts=["opt"])
    @click.option("--opt", "-o", default="", type=click.STRING)
    @click.option("--extra-opt", "-e", is_flag=True)
    def grp(opt: str, extra_opt: bool): ...

    @grp.command(cls=ClickextCommand)
    @click.option("--extra-opt", "-e", is_flag=True)
    def cmd(extra_opt: bool): ...

    runner = CliRunner()
    result = runner.invoke(grp, args_template.format(opt=opt, extra_opt=extra_opt))

    assert result.exit_code == expected_code
    assert result.output == expected_output


@pytest.mark.parametrize("global_opt", ["", "opt1", "opt2", "opt3", "cmd"])
def test_clickext_group_global_options_validation(global_opt: str):
    context = does_not_raise()

    if global_opt == "opt2":
        context = pytest.raises(ValueError, match="Subcommand option opt2 conflicts with a global option name")
    elif global_opt == "opt3":
        context = pytest.raises(
            ValueError, match="Subcommand option string --opt3 conflicts with a global option string"
        )
    elif global_opt == "cmd":
        context = pytest.raises(ValueError, match="Subcommand cmd conflicts with a global option")
    with context:

        @click.group(cls=ClickextGroup, global_opts=[global_opt] if global_opt else None)
        @click.option("--opt1", is_flag=True)
        @click.option("--opt2", is_flag=True)
        @click.option("--opt3", is_flag=True)
        @click.option("--cmd", is_flag=True)
        def grp(): ...

        @grp.command(cls=ClickextCommand)
        @click.option("--opt2", is_flag=True)
        @click.option("--opt3", "opt3_var", is_flag=True)
        def cmd(): ...


@pytest.mark.parametrize("shared_params", [None, [], ["opt"], ["undefined"]])
def test_clickext_group_shared_parameters_init(shared_params: t.Optional[list[str]]):
    context = does_not_raise()

    if shared_params and "undefined" in shared_params:
        context = pytest.raises(ValueError, match="Unknown shared parameter undefined")

    with context:

        @click.group(cls=ClickextGroup, shared_params=shared_params)
        @click.option("--opt")
        def grp(): ...


@pytest.mark.parametrize("opt", ["", "--opt", "-o"])
@pytest.mark.parametrize("cmd_name", ["cmd1", "cmd2"])
def test_clickext_group_shared_parameters_on_subcommands(cmd_name: str, opt: str):

    @click.group(cls=ClickextGroup, shared_params=["opt"])
    @click.option("--opt", "-o", is_flag=True)
    def grp(): ...

    @grp.command(cls=ClickextCommand)
    def cmd1(opt: bool):
        click.echo(f"cmd1: {opt}")

    @grp.command(cls=ClickextCommand)
    def cmd2(opt: bool):
        click.echo(f"cmd2: {opt}")

    runner = CliRunner()
    result = runner.invoke(grp, f"{cmd_name} {opt}")

    assert result.exit_code == 0
    assert result.output == f"{cmd_name}: {bool(opt)}\n"


@pytest.mark.parametrize("shared_param", ["", "opt1", "opt2", "opt3", "arg"])
def test_clickext_group_shared_parameters_validation(shared_param: str):
    context = does_not_raise()

    if shared_param == "opt2":
        context = pytest.raises(ValueError, match="Subcommand option opt2 conflicts with a shared parameter name")
    elif shared_param == "opt3":
        context = pytest.raises(
            ValueError, match="Subcommand option string --opt3 conflicts with a shared option string"
        )
    elif shared_param == "arg":
        context = pytest.raises(ValueError, match="Subcommand argument arg conflicts with a shared parameter name")

    with context:

        @click.group(cls=ClickextGroup, shared_params=[shared_param] if shared_param else None)
        @click.option("--opt1", is_flag=True)
        @click.option("--opt2", is_flag=True)
        @click.option("--opt3", is_flag=True)
        @click.option("--arg", is_flag=True)
        def grp():
            pass

        @grp.command(cls=ClickextCommand)
        @click.option("--opt2", is_flag=True)
        @click.option("--opt3", "xyz", is_flag=True)
        @click.argument("arg", nargs=1)
        def cmd():
            pass
