import logging

import click
from click.testing import CliRunner
import pytest

from clickext import DebugCommonOptionGroup


@click.group(
    cls=DebugCommonOptionGroup,
    common_options=[
        click.Option(["--foo"], is_flag=True, default=False),
        click.Option(["--bar"], is_flag=True, default=False),
    ],
)
def cli():
    pass


@cli.command()
def debug(bar, foo, debug):
    logger = logging.getLogger(__file__)
    click.echo(f"{foo}{bar}{debug}")
    logger.debug("a conditional message")


@pytest.mark.parametrize(
    ["flags", "expect_output", "expect_log"],
    [(["--foo", "--debug"], "TrueFalseTrue\n", True), (["--bar"], "FalseTrueFalse\n", False)],
)
def test_shared_options(flags, expect_output, expect_log):
    args = ["debug"]
    args.extend(flags)
    runner = CliRunner()
    result = runner.invoke(cli, args)

    assert result.exit_code == 0
    assert expect_output in result.output
    assert expect_log == ("Debug:" in result.output)
