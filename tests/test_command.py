# pylint: disable=missing-function-docstring,missing-module-docstring

import click
from click.testing import CliRunner
import pytest

from clickext import ClickextCommand


@pytest.mark.parametrize(
    ["name", "aliases", "expected"],
    [("cmd", [], []), ("cmd", ["b", "a", "c"], ["a", "b", "c"])],
    ids=["without aliases", "with aliases"],
)
def test_aliases(name: str, aliases: list[str], expected: list[str]):
    cmd = ClickextCommand(name, aliases=aliases)
    assert cmd.aliases == expected


def test_no_aliases_in_non_subcommand_help():
    cmd = ClickextCommand("cmd", aliases=["cmdalias", "otheralias"])
    runner = CliRunner()
    result = runner.invoke(cmd, ["--help"])

    assert "Aliases:\n  cmdalias\n  otheralias\n" not in result.output


@pytest.mark.parametrize(
    ["mx_opts", "args", "fail"],
    [
        (None, ["--xopt"], False),
        ([("xopt", "yopt")], ["--xopt"], False),
        ([("xopt", "yopt")], ["--xopt", "--yopt"], True),
    ],
    ids=[
        "w/out mutually exclusive opts",
        "w/ mutually exclusive opts (ok)",
        "w/ mutually exclusive opts (fail)",
    ],
)
def test_exclusive_options(mx_opts: list[tuple[str]], args: list[str], fail: bool):
    @click.command(cls=ClickextCommand, mx_opts=mx_opts)
    @click.option("--xopt", is_flag=True, default=False)
    @click.option("--yopt", is_flag=True, default=False)
    def cmd(xopt, yopt):  # pylint: disable=unused-argument
        click.echo("ok")

    runner = CliRunner()
    result = runner.invoke(cmd, args)

    if fail:
        assert result.exit_code > 0
        assert "Error: Mutually exclusive options: --xopt --yopt\n" in result.output
    else:
        assert result.exit_code == 0
        assert "ok\n" == result.output


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
    @click.command(cls=ClickextCommand)
    def cmd():
        raise initial("foobar")  # type: ignore

    runner = CliRunner()
    result = runner.invoke(cmd, catch_exceptions=False)

    assert result.output == expected
