import os
import click
import configparser
import functools


class ConfigParser:
    """
    A parser for configuration files
    """

    def __init__(self):
        pass

    def __call__(self, file_path, cmd_name):
        """
        Parse and return the configuration parameters.

        Parameters
        ----------
        file_path : str
            The path to the configuration file
        cmd_name : str
            The name of the click command

        Returns
        -------
        dict
            A dictionary containing the configuration parameters.
        """
        configParser = configparser.ConfigParser()
        configParser.read(file_path)
        return configParser


def config_callback(
    cmd_name,
    option_name,
    config_file,
    saved_callback,
    provider,
    implicit,
    ctx,
    param,
    value,
):
    """
    Callback for reading the config file.

    Also takes care of calling user specified custom callback afterwards.

    Parameters
    ----------
    cmd_name : str
        The command name.
    option_name : str
        The name of the option.
    config_file : str
        The name of the config file.
    saved_callback: callable
        User-specified callback to be called later.
    provider : callable
        A callable that parses the configuration file and returns a dictionary
        of the configuration parameters. Will be called as
        `provider(file_path, cmd_name)`. Default: `configparse_provider()`
    implicit : bool
        Whether a implicit value should be applied if no configuration option
        value was provided.
    ctx : object
        Click context.
    """
    ctx.default_map = ctx.default_map or {}
    cmd_name = cmd_name or ctx.info_name
    ctx.config = None
    if implicit:
        default_value = os.path.join(os.getcwd(), config_file)
        param.default = default_value
        value = value or default_value

    if value:
        try:
            config = provider(value, cmd_name)
        except Exception as e:
            raise click.BadOptionUsage(option_name, f"Error reading config: {e}", ctx)
        ctx.config = config
        ctx.default_map.update(config)
    return saved_callback(ctx, param, value) if saved_callback else value


def config_reader(*param_decls, **attrs):
    """
    Extends click's decorators to support configuration file support.

    Creates an option of type `click.File` expecting a configuration file path.
    Overwrites the default values for other click arguments or options
    with the value from the configuration file.

    The default name of the option is `-c`, `--config` and the default file
    is read from the current working directory, `os.getcwd`.


    cmd_name : str
        The command name. This is used to determine the configuration
        directory. Default: `ctx.info_name`
    config_file_name : str
        The name of the configuration file. Default: `'config'``
    implicit: bool
        If 'True' then implicitly create a value for the configuration option
        using the above parameters. If a configuration file exists in this
        path it will be applied even if no configuration option was suppplied
        as a CLI argument or environment variable.
        If 'False` only apply a configuration file that has been explicitely
        specified.
        Default: `False`
    parser : callable
        A callable that parses the configuration file and returns a dictionary
        of the configuration parameters. Will be called as
        `parser(file_path, cmd_name)`.
    """
    param_decls = param_decls or (
        "-c",
        "--config",
    )
    option_name = param_decls[0]

    def decorator(f):

        attrs.setdefault("is_eager", True)
        attrs.setdefault("help", "Read configuration from FILE.")
        attrs.setdefault("expose_value", False)
        implicit = attrs.pop("implicit", False)
        cmd_name = attrs.pop("cmd_name", None)
        config_file = attrs.pop("config_file_name", "config.ini")
        provider = attrs.pop("provider", ConfigParser())
        path_default_params = {
            "exists": False,
            "file_okay": True,
            "dir_okay": False,
            "writable": False,
            "readable": True,
            "resolve_path": False,
        }
        path_params = {k: attrs.pop(k, v) for k, v in path_default_params.items()}
        attrs["type"] = attrs.get("type", click.Path(**path_params))
        saved_callback = attrs.pop("callback", None)
        partial_callback = functools.partial(
            config_callback,
            cmd_name,
            option_name,
            config_file,
            saved_callback,
            provider,
            implicit,
        )
        attrs["callback"] = partial_callback
        return click.option(*param_decls, **attrs)(f)

    return decorator
