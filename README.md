# clickext

Extended features for the Python click library. Includes global logging configuration for pretty console output, command groups with shared options, and commands with aliases.


## Requirements

* Python 3.10.x
* click 8.x.x


## Installation

### Local

```
pip install --trusted-host=gitea.lojoja.com --extra-index-url=https://gitea.lojoja.com/api/packages/lojoja/pypi/simple clickext
```

### Remote

```
pip install git+ssh://github.com/lojoja/clickext@main
```

## Usage

### Logging

Logging is automatically configured when the clickext library is imported. The logging configuration formats messages and click exceptions, and colors the console output. To change the log output level, set the level of the root logger.

### Commands with aliases

Command aliases provide alternate names for a single command. Helpful for commands with long names or to shorten commands with many options/arguments. Aliased commands must be in a `clickext.AliasAwareGroup` command group. This group accepts aliased and unaliased commands.

Define commands:

```
import click
import clickext

@click.group(cls=clickext.AliasAwareGroup)
def cli():
    pass

@cli.command(cls=clickext.AliasCommand, aliases=["a"])
def aliased():
    click.echo("aliased or a")

@cli.command():
def unaliased():
    click.echo("only unaliased")
```

Call commands:

```
> cli aliased
aliased or a
> cli a
aliased or a
> cli unaliased
only unaliased
```

### Commands with common options

Common options provide a way to configure and parse global options that can appear after any subcommand in the group.

Define commands:

```
import click
import clickext

@click.group(cls=clickext.CommonOptionGroup, common_options=[
    click.Option(["--excited"], is_flag=True, default=False)
])
def cli():
    pass

@cli.command()
def hello(excited):
    punctuation = '!' if excited else '.'
    click.echo(f"Hello{punctuation}")

@cli.command()
def hi(excited):
    punctuation = '!' if excited else '.'
    click.echo(f"Hi{punctuation}")
```

Call commands:

```
> cli hello
Hello.
> cli hello --excited
Hello!
> cli hi
Hi.
> cli hi --excited
Hi!
```

### Command with shared options, debug option

Adds a `--debug` flag option to all commands in the command group for more verbose console output. Optionally, additional shared options can be defined.

Define commands:

```
import logging
import click
import clickext

logger = logging.getLogger(__name__)

@click.group(cls=clickext.DebugCommonOptionGroup, common_options=[
    click.Option(["--excited"], is_flag=True, default=False)
])
def cli():
  pass

@cli.command()
def hello(excited, debug):
    punctuation = '!' if excited else '.'
    logger.debug('Debug is enabled')
    click.echo(f"Hello{punctuation}")
```

Call commands:

```
> cli hello
Hello.
> cli hello --debug
Debug: Debug is enabled
Hello.
```

## License

clickext is released under the [MIT License](./LICENSE)
