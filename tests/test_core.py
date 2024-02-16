# pylint: disable=missing-module-docstring,missing-function-docstring,unused-argument

from contextlib import nullcontext as does_not_raise
import errno
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


@pytest.mark.parametrize(
    "exc_class",
    [
        BrokenPipeError,  # used to identifiy the test case; actually tests OSError with errno=errno.EPIPE
        click.Abort,
        click.ClickException,
        click.exceptions.Exit,
        EOFError,
        KeyboardInterrupt,
        OSError,
        RuntimeError,
        TypeError,
    ],
)
@pytest.mark.parametrize("catch_exceptions", [True, False])
def test_clickext_command_invoke(catch_exceptions: bool, exc_class: type[Exception]):
    if not catch_exceptions and exc_class in [OSError, RuntimeError, TypeError]:
        context = pytest.raises(exc_class, match="msg")
    else:
        context = does_not_raise()

    if exc_class in [EOFError, KeyboardInterrupt]:
        expected_output = "\nAborted!\n"
    elif exc_class == click.Abort:
        expected_output = "Aborted!\n"
    elif exc_class == click.exceptions.Exit:
        expected_output = "msg\n"
    elif exc_class == BrokenPipeError:  # click catches this and exits
        expected_output = ""
    else:
        expected_output = "Error: msg\n"

    @click.command(cls=ClickextCommand, catch_exceptions=catch_exceptions)
    def cmd():
        if exc_class == BrokenPipeError:
            exc = OSError("msg")
            exc.errno = errno.EPIPE
            raise exc
        raise exc_class("msg")

    runner = CliRunner()

    with context:
        result = runner.invoke(cmd, catch_exceptions=False)

    if isinstance(context, does_not_raise):
        assert result.exit_code == 1
        assert result.output == expected_output


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
    ["args_template", "should_fail"],
    [
        ["{opt}", True],
        ["{opt} cmd", False],
        ["{opt} cmd {extra_opt}", False],
        ["{opt} {extra_opt} cmd", False],
        ["{opt} {extra_opt} cmd {extra_opt}", False],
        ["{extra_opt} cmd {opt}", False],
        ["{extra_opt} cmd {opt} {extra_opt}", False],
        ["{extra_opt} cmd {extra_opt} {opt}", False],
        ["{extra_opt} {opt} cmd", False],
        ["{extra_opt} {opt} cmd {extra_opt}", False],
        ["cmd", False],
        ["cmd {opt}", False],
        ["cmd {opt} {extra_opt}", False],
        ["cmd {extra_opt}", False],
        ["cmd {extra_opt} {opt}", False],
    ],
)
def test_clickext_group_global_options_parse_flag(args_template: str, opt: str, extra_opt: str, should_fail: bool):
    expected_code = 0
    expected_output = ""

    if should_fail:
        expected_code = 2
        expected_output = (
            "Usage: grp [OPTIONS] COMMAND [ARGS]...\nTry 'grp --help' for help.\n\nError: Missing command.\n"
        )

    @click.group(cls=ClickextGroup, global_opts=["opt"])
    @click.option("--opt", "-o", is_flag=True)
    @click.option("--extra-opt", "-e", is_flag=True)
    def grp(opt: bool, extra_opt: bool): ...

    @grp.command(cls=ClickextCommand)
    @click.option("--extra-opt", "-e", is_flag=True)
    def cmd(extra_opt: bool): ...

    runner = CliRunner()
    result = runner.invoke(grp, args_template.format(opt=opt, extra_opt=extra_opt))

    assert result.exit_code == expected_code
    assert result.output == expected_output


@pytest.mark.parametrize("value", ["a", "x"])
@pytest.mark.parametrize("extra_opt", ["--extra-opt", "-e"])
@pytest.mark.parametrize("opt", ["--opt", "-o"])
@pytest.mark.parametrize(
    ["args_template", "failure_reason"],
    [
        ("{opt}", "missing_argument"),
        ("{opt} cmd", "missing_command"),
        ("{opt} cmd {extra_opt}", "missing_command"),
        ("{opt} {extra_opt} cmd", ""),
        ("{opt} {extra_opt} cmd {extra_opt}", ""),
        ("{opt} {val}", "missing_command"),
        ("{opt} {val} cmd", ""),
        ("{opt} {val} cmd {extra_opt}", ""),
        ("{opt} {val} {extra_opt} cmd", ""),
        ("{opt} {val} {extra_opt} cmd {extra_opt}", ""),
        ("cmd", ""),
        ("cmd {opt}", "missing_argument"),
        ("cmd {opt} {extra_opt}", ""),
        ("cmd {opt} {val}", ""),
        ("cmd {opt} {val} {extra_opt}", ""),
        ("cmd {extra_opt}", ""),
        ("cmd {extra_opt} {opt}", "missing_argument"),
        ("cmd {extra_opt} {opt} {val}", ""),
        ("{extra_opt} cmd", ""),
        ("{extra_opt} cmd {opt}", "missing_argument"),
        ("{extra_opt} cmd {opt} {extra_opt}", ""),
        ("{extra_opt} cmd {opt} {val}", ""),
        ("{extra_opt} cmd {opt} {val} {extra_opt}", ""),
        ("{extra_opt} cmd {extra_opt}", ""),
        ("{extra_opt} cmd {extra_opt} {opt}", "missing_argument"),
        ("{extra_opt} cmd {extra_opt} {opt} {val}", ""),
    ],
)
def test_clickext_group_global_options_parse_value(
    args_template: str, failure_reason: str, opt: str, extra_opt: str, value: str
):
    expected_code = 0
    expected_output = ""

    if failure_reason:
        expected_code = 2
        if failure_reason == "missing_command":
            expected_output = (
                "Usage: grp [OPTIONS] COMMAND [ARGS]...\nTry 'grp --help' for help.\n\nError: Missing command.\n"
            )
        else:
            expected_output = f"Error: Option '{opt}' requires an argument.\n"

    @click.group(cls=ClickextGroup, global_opts=["opt"])
    @click.option("--opt", "-o", default="a")
    @click.option("--extra-opt", "-e", is_flag=True)
    def grp(opt: str, extra_opt: bool): ...

    @grp.command(cls=ClickextCommand)
    @click.option("--extra-opt", "-e", is_flag=True)
    def cmd(extra_opt: bool): ...

    runner = CliRunner()
    result = runner.invoke(grp, args_template.format(opt=opt, val=value, extra_opt=extra_opt))

    assert result.exit_code == expected_code
    assert result.output == expected_output


@pytest.mark.parametrize("values", [("a", "b"), ("x", "y")])
@pytest.mark.parametrize("extra_opt", ["--extra-opt", "-e"])
@pytest.mark.parametrize("opt", ["--opt", "-o"])
@pytest.mark.parametrize(
    ["args_template", "failure_reason"],
    [
        ("{opt}", "missing_argument"),
        ("{opt} cmd", "missing_argument"),
        ("{opt} cmd {extra_opt}", "missing_command"),
        ("{opt} {extra_opt} cmd", "missing_command"),
        ("{opt} {extra_opt} cmd {extra_opt}", "missing_command"),
        ("{opt} {val1} {val2}", "missing_command"),
        ("{opt} {val1} {val2} cmd", ""),
        ("{opt} {val1} {val2} cmd {extra_opt}", ""),
        ("{opt} {val1} {val2} {extra_opt} cmd", ""),
        ("{opt} {val1} {val2} {extra_opt} cmd {extra_opt}", ""),
        ("cmd", ""),
        ("cmd {opt}", "missing_argument"),
        ("cmd {opt} {extra_opt}", "missing_argument"),
        ("cmd {opt} {val1} {val2}", ""),
        ("cmd {opt} {val1} {val2} {extra_opt}", ""),
        ("cmd {extra_opt}", ""),
        ("cmd {extra_opt} {opt}", "missing_argument"),
        ("cmd {extra_opt} {opt} {val1} {val2}", ""),
        ("{extra_opt} cmd", ""),
        ("{extra_opt} cmd {opt}", "missing_argument"),
        ("{extra_opt} cmd {opt} {extra_opt}", "missing_argument"),
        ("{extra_opt} cmd {opt} {val1} {val2}", ""),
        ("{extra_opt} cmd {opt} {val1} {val2} {extra_opt}", ""),
        ("{extra_opt} cmd {extra_opt}", ""),
        ("{extra_opt} cmd {extra_opt} {opt}", "missing_argument"),
        ("{extra_opt} cmd {extra_opt} {opt} {val1} {val2}", ""),
    ],
)
def test_clickext_group_global_options_parse_value_nargs(
    args_template: str, failure_reason: str, opt: str, extra_opt: str, values: tuple[str, str]
):
    expected_code = 0
    expected_output = ""

    if failure_reason:
        expected_code = 2
        if failure_reason == "missing_command":
            expected_output = (
                "Usage: grp [OPTIONS] COMMAND [ARGS]...\nTry 'grp --help' for help.\n\nError: Missing command.\n"
            )
        else:
            expected_output = f"Error: Option '{opt}' requires 2 arguments.\n"

    @click.group(cls=ClickextGroup, global_opts=["opt"])
    @click.option("--opt", "-o", default=("a", "b"), nargs=2)
    @click.option("--extra-opt", "-e", is_flag=True)
    def grp(opt: str, extra_opt: bool): ...

    @grp.command(cls=ClickextCommand)
    @click.option("--extra-opt", "-e", is_flag=True)
    def cmd(extra_opt: bool): ...

    runner = CliRunner()
    result = runner.invoke(grp, args_template.format(opt=opt, val1=values[0], val2=values[1], extra_opt=extra_opt))

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
