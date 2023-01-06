# pylint: disable=missing-function-docstring,missing-module-docstring

import click
from click.testing import CliRunner
import pytest

from clickext import ClickextCommand, ClickextGroup


def test_group_does_not_accept_click_command():
    with pytest.raises(TypeError, match="Only 'ClickextCommand's can be registered with a 'ClickextGroup'"):

        @click.group(cls=ClickextGroup)
        def cli():
            pass

        @cli.command()
        def cmd():
            pass


@pytest.mark.parametrize(
    ["global_opts", "args", "expected_output", "expected_code"],
    [
        # no globals
        ([], ["--foo", "cmd", "--bar"], "foo:True / bar:False / baz:\nbar:True\n", 0),
        # global flag option
        (["foo"], ["--foo", "cmd"], "foo:True / bar:False / baz:\nbar:False\n", 0),
        (["foo"], ["--foo", "cmd", "--bar"], "foo:True / bar:False / baz:\nbar:True\n", 0),
        (["foo"], ["cmd", "--foo"], "foo:True / bar:False / baz:\nbar:False\n", 0),
        (["foo"], ["cmd", "--foo", "--bar"], "foo:True / bar:False / baz:\nbar:True\n", 0),
        # global value option
        (["baz"], ["--baz", "x", "cmd"], "foo:False / bar:False / baz:x\nbar:False\n", 0),
        (["baz"], ["--baz", "x", "cmd", "--bar"], "foo:False / bar:False / baz:x\nbar:True\n", 0),
        (["baz"], ["cmd", "--baz", "x"], "foo:False / bar:False / baz:x\nbar:False\n", 0),
        (["baz"], ["cmd", "--bar", "--baz", "x"], "foo:False / bar:False / baz:x\nbar:True\n", 0),
        # global value option, missing value
        (["baz"], ["--baz", "cmd"], "Error: Missing command.\n", 2),
        (["baz"], ["--baz", "cmd", "--bar"], "Error: Missing command.\n", 2),
        (["baz"], ["cmd", "--baz"], "Error: Missing command.\n", 2),
        (["baz"], ["cmd", "--baz", "--bar"], "Error: Missing command.\n", 2),
    ],
    ids=[
        "no global options",
        "after group, no subcommand arg",
        "after group, subcommand arg",
        "after subcommand, no subcommand arg",
        "after subcommand, subcommand arg",
        "after group, with value, no subcommand arg",
        "after group, with value, subcommand arg",
        "after subcommand, with value, no subcommand arg",
        "after subcommand, with value, subcommand arg",
        "after group, missing value, no subcommand arg",
        "after group, missing value, subcommand arg",
        "after subcommand, missing value, no subcommand arg",
        "after subcommand, missing value, subcommand arg",
    ],
)
def test_global_option_parsing(global_opts: list[str], args: list[str], expected_output: str, expected_code: int):
    @click.group(cls=ClickextGroup, global_opts=global_opts)
    @click.option("--foo", "-f", is_flag=True)
    @click.option("--bar", "-b", is_flag=True)
    @click.option("--baz", "-z", default="", type=click.STRING)
    @click.option("--cmd", "-c", is_flag=True)
    def cli(foo, bar, baz, cmd):  # pylint: disable=disallowed-name,unused-argument
        click.echo(f"foo:{foo} / bar:{bar} / baz:{baz}")

    @cli.command(cls=ClickextCommand)
    @click.option("--bar", "-b", is_flag=True)
    def cmd(bar):  # pylint: disable=disallowed-name
        click.echo(f"bar:{bar}")

    runner = CliRunner()
    result = runner.invoke(cli, args)

    assert result.exit_code == expected_code
    assert expected_output in result.output


@pytest.mark.parametrize(
    ["global_opts", "exception", "expected_output"],
    [
        (["abc"], ValueError, "Unknown global option abc"),
        (["bat"], TypeError, "Invalid global option bat; global options must be a 'click.Option'"),
        (["cmd"], ValueError, "Subcommand cmd conflicts with a global option"),
        (["bar"], ValueError, "Subcommand option bar conflicts with a global option name"),
        (["baz"], ValueError, "Subcommand option string --baz conflicts with a global option string"),
    ],
    ids=[
        "undefined",
        "invalid type",
        "same as subcommand name",
        "same as subcommand option",
        "same as subcommand option string",
    ],
)
def test_global_option_validation(global_opts: list[str], exception: Exception, expected_output: str):
    with pytest.raises(exception, match=expected_output):  # type:ignore

        @click.group(cls=ClickextGroup, global_opts=global_opts)
        @click.option("--foo", is_flag=True)
        @click.option("--bar", is_flag=True)
        @click.option("--baz", is_flag=True)
        @click.option("--cmd", is_flag=True)
        @click.argument("bat", nargs=1)
        def cli(foo, bar, baz, cmd, bat):  # pylint: disable=disallowed-name,unused-argument
            pass

        @cli.command(cls=ClickextCommand)
        @click.option("--bar", is_flag=True)
        @click.option("--baz", "xyz", is_flag=True)
        def cmd(bar, xyz):  # pylint: disable=disallowed-name,unused-argument
            pass


@pytest.mark.parametrize(
    ["initial", "expected"],
    [
        (EOFError, "\nAborted!\n"),
        (KeyboardInterrupt, "\nAborted!\n"),
        (click.ClickException, "Error: foobar\n"),
        (click.Abort, "Aborted!\n"),
        (click.exceptions.Exit, "foobar\n"),
        (RuntimeError, "Error: foobar\n"),
        (ValueError, "Error: foobar\n"),
    ],
    ids=["eof", "kbd", "click exception", "click abort", "click exit", "runtime error", "value error"],
)
def test_exceptions_caught(initial: Exception, expected: str):
    @click.group(cls=ClickextGroup, invoke_without_command=True)
    def cli():
        raise initial("foobar")  # type: ignore

    runner = CliRunner()
    result = runner.invoke(cli, catch_exceptions=False)

    assert result.output == expected


@pytest.mark.parametrize(
    ["args", "expected_output"],
    [
        (["--help"], "Commands:\n  cmd (sc)\n"),
        (["cmd", "--help"], "Options:\n  --foo\n"),
        (["cmd", "--help"], "Aliases:\n  sc\n"),
    ],
    ids=["command aliases in group help", "global options in subcommand help", "aliases in subcommand help"],
)
def test_group_help(args: list[str], expected_output: str):
    @click.group(cls=ClickextGroup, global_opts=["foo"])
    @click.option("--foo", is_flag=True)
    def cli(foo):  # pylint: disable=disallowed-name,unused-argument
        pass

    @cli.command(cls=ClickextCommand, aliases=["sc"])
    def cmd():
        pass

    @cli.command(cls=ClickextCommand, hidden=True)
    def hid():
        pass

    runner = CliRunner()
    result = runner.invoke(cli, args)
    assert expected_output in result.output
