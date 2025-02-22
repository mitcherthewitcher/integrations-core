# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click


@click.group(short_help='Manage the config file')
def config():
    pass


@config.command(short_help='Edit the config file with your default editor')
@click.pass_obj
def edit(app):
    """Edit the config file with your default editor."""
    click.edit(filename=str(app.config_file.path))


@config.command(short_help='Open the config location in your file manager')
@click.pass_obj
def explore(app):
    """Open the config location in your file manager."""
    click.launch(str(app.config_file.path), locate=True)


@config.command(short_help='Show the location of the config file')
@click.pass_obj
def find(app):
    """Show the location of the config file."""
    app.display(str(app.config_file.path))


@config.command(short_help='Show the contents of the config file')
@click.option('--all', '-a', 'all_keys', is_flag=True, help='Do not scrub secret fields')
@click.pass_obj
def show(app, all_keys):
    """Show the contents of the config file."""
    if not app.config_file.path.is_file():  # no cov
        app.display_critical('No config file found! Please try `ddev config restore`.')
    else:
        from rich.syntax import Syntax

        text = app.config_file.read() if all_keys else app.config_file.read_scrubbed()
        app.display_raw(Syntax(text.rstrip(), 'toml', background_color='default'))


@config.command(short_help='Update the config file with any new fields')
@click.pass_obj
def update(app):  # no cov
    """Update the config file with any new fields."""
    app.config_file.update()
    app.display_success('Settings were successfully updated.')


@config.command(short_help='Restore the config file to default settings')
@click.pass_obj
def restore(app):
    """Restore the config file to default settings."""
    app.config_file.restore()
    app.display_success('Settings were successfully restored.')


@config.command('set', short_help='Assign values to config file entries')
@click.argument('key')
@click.argument('value', required=False)
@click.pass_obj
def set_value(app, key, value):
    """
    Assign values to config file entries. If the value is omitted,
    you will be prompted, with the input hidden if it is sensitive.
    """
    from fnmatch import fnmatch

    import tomlkit

    from ddev.config.model import ConfigurationError, RootConfig
    from ddev.config.utils import SCRUBBED_GLOBS, create_toml_document, save_toml_document, scrub_config

    scrubbing = any(fnmatch(key, glob) for glob in SCRUBBED_GLOBS)
    if value is None:
        value = click.prompt(f'Value for `{key}`', hide_input=scrubbing)

    if (fnmatch(key, 'repos.*') or fnmatch(key, 'repos.*.path')) and not value.startswith('~'):
        value = os.path.abspath(value)

    user_config = new_config = tomlkit.parse(app.config_file.read())

    data = [value]
    data.extend(reversed(key.split('.')))
    key = data.pop()
    value = data.pop()

    # Use a separate mapping to show only what has changed in the end
    branch_config_root = branch_config = {}

    # Consider dots as keys
    while data:
        default_branch = {value: ''}
        branch_config[key] = default_branch
        branch_config = branch_config[key]

        new_value = new_config.get(key)
        if not hasattr(new_value, 'get'):
            new_value = default_branch

        new_config[key] = new_value
        new_config = new_config[key]

        key = value
        value = data.pop()

    if value.startswith(('{', '[')):
        from ast import literal_eval

        value = literal_eval(value)

    branch_config[key] = new_config[key] = value

    # https://github.com/sdispater/tomlkit/issues/48
    if new_config.__class__.__name__ == 'Table':  # no cov
        table_body = getattr(new_config.value, 'body', [])
        possible_whitespace = table_body[-2:]
        if len(possible_whitespace) == 2:
            for key, item in possible_whitespace:
                if key is not None:
                    break
                if item.__class__.__name__ != 'Whitespace':
                    break
            else:
                del table_body[-2]

    try:
        RootConfig(user_config).parse_fields()
    except ConfigurationError as e:
        app.display_error(str(e))
        app.abort()

    save_toml_document(user_config, app.config_file.path)
    if scrubbing:
        scrub_config(branch_config_root)

    rendered_changed = tomlkit.dumps(create_toml_document(branch_config_root)).rstrip()

    from rich.syntax import Syntax

    app.display_success('New setting:')
    app.display_raw(Syntax(rendered_changed, 'toml', background_color='default'))
