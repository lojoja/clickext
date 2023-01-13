# clickext

Extended features for the Python click library. Includes global logging configuration and error handling for pretty console output, aliased commands, command groups with global and shared subcommand options, mutually exclusive options, verbosity level options, and a configuration file option.


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

### Logging and Error Messages

Logging wraps the `click.echo` and patches `click.ClickException` and `click.UsageError` to emit console-aware colored messages at different log levels. The log level determines which messages are printed to the console. A `QUIET` log level is defined to suppress all output from the program itself, though messages generated outside the program may still print. The default log level is `logging.INFO`.

```
import logging
import clickext

logger = logging.getLogger("my_logger")
clickext.init_logging(logger)
```

### Commands with aliases

Command aliases provide alternate names for a single command. Helpful for commands with long names or to shorten commands with many options/arguments. Aliased commands must be in a `clickext.ClickextGroup` command group.

Define command:

```
import click
import clickext

@click.group(cls=clickext.ClickextGroup)
def cli():
    pass

@cli.command(cls=clickext.ClickextCommand, aliases=["c"])
def cmd():
    pass
```

### Mutually exclusive options

Mutually exclusive options prevent two or more options being passed together. Shared and command-specific options can be mutually exclusive. Command group global options can be mutually exclusive with other group options, but not with shared or subcommand options.

```
import click
import clickext

@click.command(cls=clickext.ClickextCommand, mx_opts=[("foo", "bar")])
@click.option("--foo", is_flag=True)
@click.option("--bar", is_flag=True)
def cmd(foo, bar):
    pass
```

### Shared Parameters

Shared parameters are parameters defined at the group level that are added to all subcommands in the group, but not to the group itself.

```
import click
import clickext

@click.group(cls=clickext.ClickextGroup, shared_params=["foo", "bar"])
@click.option("--foo", is_flag=True)
@click.option("--bar", is_flag=True)
def cli():
    pass

@cli.command(cls=clickext.ClickextCommand)
def cmd(foo, bar):
    pass
```

### Group Global Options

Global options are group-level options that can be passed to any subcommand in the group. These options are extracted from the passed arguments before parsing and processed at the group level regardless of where they originally appeared. Global options cannot have the same name as a subcommand or subcommand option; options that accept values should not accept values with the same name as a subcommand.

```
import click
import clickext

@click.group(cls=clickext.ClickextGroup, global_opts=["foo", "bar"])
@click.option("--foo", is_flag=True)
@click.option("--bar", is_flag=True)
def cli(foo, bar):
    pass

@cli.command(cls=clickext.ClickextCommand)
def cmd():
    pass
```

### Config Option

The `config_option` provides a mechanism for loading configuration from a JSON, TOML, or YAML file and storing it on `ctx.obj`. An optional `processor` can be provided to handle the raw parsed data.

```
import click
import clickext

def config_processor(data):
    pass

@click.command(cls=clickext.Command)
@config_option('/usr/local/etc/config.json', processor=config_processor)
@click.pass_obj
def cmd(obj)
    pass
```

### Verbose and Verbosity Options

The `verbose_option` provides a simple verbosity toggle between the `logging.DEBUG` and default log level output. The `verbosity_option` provides a configurable verbosity level that can be sent to any log level by passing that level name as the argument. The clickext custom level `QUIET` can also be set.

```
import logging
import click
import clickext

logger = logging.getLogger(__package__)

@click.command(cls=clickext.ClickextCommand)
@verbose_option(logger)
def cmd():
    pass
```

## License

clickext is released under the [MIT License](./LICENSE)
