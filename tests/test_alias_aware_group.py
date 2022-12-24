import click
from click.testing import CliRunner
import pytest

from clickext import AliasCommand, AliasAwareGroup


@click.group(cls=AliasAwareGroup)
def cli():
    pass


@cli.command(cls=AliasCommand, aliases=["a", "b"])
def aliased():
    click.echo("aliased")


@cli.command()
def unaliased():
    click.echo("unaliased")


@pytest.mark.parametrize(
    ["cmd", "expected"],
    [("aliased", "aliased\n"), ("a", "aliased\n"), ("b", "aliased\n"), ("unaliased", "unaliased\n")],
)
def test_resolve_command(cmd, expected):
    runner = CliRunner()
    result = runner.invoke(cli, [cmd])
    assert result.exit_code == 0
    assert result.output == expected


def test_help_output():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "aliased (a,b)" in result.output
    assert "unaliased" in result.output
