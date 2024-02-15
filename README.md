# clickext

Extended features for the Python [click](https://github.com/pallets/click) library. Includes global logging configuration and error handling for pretty console output, aliased commands, command groups with global and shared subcommand options, mutually exclusive options, verbosity level options, and a configuration file option.

## Requirements

- Python 3.10.x, 3.11.x
- click 8.x.x

## Installation

```
pip install clickext
```

## Usage

### Logging and Error Messages

_This functionality is disabled by default. It must be explicitly enabled by calling `clickext.init_logging` or using the `clickext.verbose` or `clickext.verbosity` decorators on a command._

The logging facility provides a way to capture all informational output, emit console-friendly messages, and control the output that is displayed based on the logging level. `click.ClickException`, `click.UsageError`, their children, warnings issued by `warning.warn` and any uncaught exceptions are handled by the `clickext.log.ConsoleHandler`. Exception information, including the traceback, is available when the log level is set to `logging.DEBUG`. Higher log levels will only print a user-friendly error message. The default level is `logging.INFO`.

All informational messages intended for the console that an application user may want to suppress should be sent in a logging call rather than direct calls to `print`, `click.echo`, or similar, so they can be handled and displayed consistently according to the logging configuration. Messages that should always be displayed (e.g., the expected result of an invoked command) should be displayed with `click.echo` and _not_ sent to a logger.

Messages are formatted by default with a styled log level prefix followed by the message, except for `logging.INFO` level messages which are not prefixed. The style for each level can be customized by passing a mapping of log levels to `click.style` parameters in the `clickext.init_logging` call. Setting a level to `None` will remove the prefix and styles from the message. For example: `{logging.INFO: {"fg": "green"}, logging.DEBUG: None}` will format `logging.INFO` level messages as "Info: {msg}", with "Info:" in green text, and `logging.DEBUG` messages as "{msg}" with no prefix.

An additional log level named `QUIET` is defined when logging is initialized and can be used to provide a "quiet mode" that hides all informational output sent to a logger.

Logging is configured on the root logger in order to capture and format all logging and warning output regardless of where it originates. Any existing configuration will be replaced by the clickext logging facility. Additional handlers that do not write to stdout/stderr can be attached to the application logger normally, and to the root logger by passing them in the `clickext.init_logging` call. The application logger level and `propagate` properties are configured automatically when logging is initialized and should not be changed.

Example:

```
import logging
import click
import clickext

logger = logging.getLogger("__package__")
clickext.init_logging(logger, logging.INFO)

@click.command(cls=clickext.ClickextCommand)
def cmd():
    logger.info("some basic info")
    logger.error("uh-oh")
    logger.debug("secrets live here")
```

Output:

```
$ cmd
some basic info
Error: uh-oh
```

### Commands with aliases

Command aliases provide alternate names for a single command. This is helpful for commands with long names or to shorten commands with many options/arguments. Aliased commands must be in a `clickext.ClickextGroup` command group.

Example:

```
import click
import clickext

@click.group(cls=clickext.ClickextGroup)
def cli():
    pass

@cli.command(cls=clickext.ClickextCommand, aliases=["c"])
def cmd():
    click.echo("ok!")
```

Output:

```
$ cli cmd
ok!
$ cli c
ok!
```

### Mutually exclusive options

Mutually exclusive options prevent two or more options being passed together. Shared and command-specific options can be mutually exclusive. Global group options can be mutually exclusive with other group options, but not with shared parameters or subcommand options.

Example:

```
import click
import clickext

@click.command(cls=clickext.ClickextCommand, mx_opts=[("foo", "bar")])
@click.option("--foo", is_flag=True)
@click.option("--bar", is_flag=True)
def cmd(foo, bar):
    pass
```

Output:

```
$ cmd --foo --bar
Usage: cmd [OPTIONS]"
Try 'cmd --help' for help."

Error: Mutually exclusive options: --foo --bar
```

### Shared Parameters

Shared parameters are parameters required by all subcommands in a group. They are defined at the group level and automatically added to all subcommands, but not the group itself. Subcommand signatures must accept the shared parameters as arguments unless the parameter was defined with `expose_value=False`.

Example:

```
import click
import clickext

@click.group(cls=clickext.ClickextGroup, shared_params=["foo", "bar"])
@click.option("--foo", is_flag=True)
@click.option("--bar", is_flag=True)
def cli():
    pass

@cli.command(cls=clickext.ClickextCommand)
def cmd1(foo, bar):
    for value in [foo, bar]:
        if value:
            click.echo("Yes!")
        else:
            click.echo("No!")

@cli.command(cls=clickext.ClickextCommand)
def cmd2(foo, bar):
    for value in [foo, bar]:
        if value:
            click.echo("Also Yes!")
        else:
            click.echo("Also No!")
```

Output:

```
$ cli cmd1 --foo
Yes!
No!
$ cli cmd2 --foo --bar
Also Yes!
Also Yes!
```

### Global Options

Global options are group-level options that may be passed to any subcommand in the group. The options are extracted from the passed arguments before parsing and processed at the group level regardless of where they originally appeared. Global options cannot have the same name as a subcommand or subcommand option; options that accept values should not accept values with the same name as a subcommand.

Example:

```
import click
import clickext

@click.group(cls=clickext.ClickextGroup, global_opts=["foo", "bar"])
@click.option("--foo", is_flag=True)
@click.option("--bar", is_flag=True)
def cli(foo, bar):
    for value in [foo, bar]:
        if value:
            click.echo("Yes!")
        else:
            click.echo("No!")

@cli.command(cls=clickext.ClickextCommand)
@click.option("--baz", is_flag=True)
def cmd(baz):
    if baz:
        click.echo("Yes baz!")
    else:
        click.echo("No baz!")
```

Output:

```
$ cli --foo
Yes!
No!
$ cli cmd --bar
No!
Yes!
No baz!
$ cli --bar cmd --baz --foo
Yes!
Yes!
Yes baz!
```

### Config Option

The `clickext.config_option` provides a mechanism for loading configuration from a JSON, TOML, or YAML file and storing it on `click.Context.obj`. An optional `processor` can be provided to prepare the parsed data for application use.

Example config.json:

```
{
    "a": "x",
    "b": "y",
    "c": "z"
}
```

Example:

```
import click
import clickext

def exclaim(data):
    for k, v in data.items():
        data[k] = v + "!"
    return data

@click.command(cls=clickext.ClickextCommand)
@clickext.config_option('config.json', processor=exclaim)
@click.pass_obj
def cmd(obj)
    for k, v in obj.items():
        click.echo(k + ": " + v)
```

Output:

```
$ cmd
a: x!
b: y!
c: z!
```

### Verbose and Verbosity Options

The `clickext.verbose_option` provides a simple verbosity toggle between `logging.DEBUG` and the default log level output (`logging.INFO`, by default). The `clickext.verbosity_option` provides a configurable verbosity level that can be set to any log level by passing that level name as the argument. Logging configuration adds a `QUIET` level that can be used to provide a "quiet mode" with no optional output. When either of these options is used logging will be enabled and configured automatically; it is not necessary to call `clickext.init_logging` beforehand.

Example verbose switch:

```
import logging
import click
import clickext

logger = logging.getLogger(__package__)

@click.command(cls=clickext.ClickextCommand)
@clickext.verbose_option(logger)
def cmd():
    logger.debug("a debug message")
    logger.info("an info message")
```

Output:

```
$ cmd
an info message
$ cmd --verbose
Debug: a debug message
an info message
```

Example verbosity switch:

```
import logging
import click
import clickext

logger = logging.getLogger(__package__)

@click.command(cls=clickext.ClickextCommand)
@clickext.verbosity_option(logger)
def cmd():
    logger.info("an info message")
    logger.warning("a warning message")
```

Output:

```
$ cmd
an info message
Warning: a warning message
$ cmd --verbosity WARNING
Warning: a warning message
$ cmd --verbosity QUIET
$
```

## License

clickext is released under the [MIT License](./LICENSE)
