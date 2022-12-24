import click
from click.testing import CliRunner
import pytest

from clickext import CommonOptionGroup


@click.group(
    cls=CommonOptionGroup,
    common_options=[
        click.Option(["--foo"], is_flag=True, default=False),
        click.Option(["--bar"], is_flag=True, default=False),
    ],
)
def cli():
    pass


@cli.command()
def shared(bar, foo):
    click.echo(f"{foo}{bar}")


@cli.command()
@click.option("--baz", default="baz")
def unshared(baz, bar, foo):
    click.echo(f"{foo}{bar}{baz}")


@pytest.mark.parametrize(
    ["flags", "expected"], [(["--foo"], "TrueFalse\n"), (["--bar"], "FalseTrue\n"), (["--foo", "--bar"], "TrueTrue\n")]
)
def test_shared_options(flags, expected):
    args = ["shared"]
    args.extend(flags)
    runner = CliRunner()
    result = runner.invoke(cli, args)

    assert result.exit_code == 0
    assert result.output == expected


def test_shared_options_with_unshared():
    runner = CliRunner()
    result = runner.invoke(cli, ["unshared", "--foo"])

    assert result.exit_code == 0
    assert result.output == "TrueFalsebaz\n"
