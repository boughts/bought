"""
Main entry point for the bought command and application.
"""

import os
import sys
import json
import click
import pathlib
import configparser

from selenium import webdriver
from bought.config import config_reader
from bought.websites.newegg import Newegg


@click.group(chain=True, invoke_without_command=True, no_args_is_help=True)
@click.option(
    "-d",
    "--driver",
    type=click.Choice(["chrome", "chromium", "firefox"], case_sensitive=False),
    help="Run bought with the selected driver.",
)
@click.option(
    "-h",
    "--headless",
    is_flag=True,
    help="Run bought without a GUI.",
)
@config_reader()
@click.version_option()
@click.pass_context
def main(ctx, driver, headless):
    """A bot that purchases items online, rendering them bought.

    By default, bought uses the parameters specified in config.ini for
    configuration but these can also be specified via CLI.

    Made with <3 by jsonV
    """
    ctx.ensure_object(dict)

    drive = None
    no_head = False
    invoke_newegg = False
    wait = None

    # Override defaults if config.ini variable specified
    if ctx.config:
        driver = ctx.config["Main"]["Driver"].lower()
        if ctx.config["Main"]["Headless"].lower() == "true":
            no_head = True
        if ctx.config["Newegg"]["Enabled"].lower() == "true":
            items = ctx.config["Newegg"]["Items"]
            invoke_newegg = True
        if ctx.config["Main"]["ImplicitWait"]:
            wait = int(ctx.config["Main"]["ImplicitWait"])
    # Override if CLI argument specified
    if driver:
        drive = driver
    if headless:
        no_head = headless

    if drive == "firefox":
        options = webdriver.FirefoxOptions()
    elif drive == "chrome" or drive == "chromium":
        options = webdriver.ChromeOptions()
    else:
        raise ValueError("Browser not specified!")

    if no_head:
        options.set_headless()
    options.page_load_strategy = "eager"
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:83.0) Gecko/20100101 Firefox/83.0"
    )
    if drive == "firefox":
        driver = webdriver.Firefox(firefox_options=options)
    elif drive == "chrome" or drive == "chromium":
        driver = webdriver.Chrome(chrome_options=options)
    driver.implicitly_wait(wait)
    ctx.obj["driver"] = driver

    if invoke_newegg:
        ctx.obj["config"] = ctx.config
        ctx.invoke(newegg, items=items)


@main.command()
@click.option(
    "-i",
    "--items",
    default=[],
    help="A list of Newegg item numbers.",
)
@click.help_option()
@click.pass_context
def newegg(ctx, items):
    """Bought newegg items."""
    newegg = Newegg(ctx.obj, items)
    newegg.bought()
