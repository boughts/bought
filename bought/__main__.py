"""
Main entry point for the bought command and application.
"""

import os
import sys
import json
import click
import logging
import pathlib
import configparser

from urllib3.connectionpool import log as urllibLogger
from selenium import webdriver
from selenium.webdriver.remote.remote_connection import LOGGER as selenium_logger
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
    fp = None
    no_head = False
    invoke_newegg = False
    wait = None
    logging.basicConfig(
        filemode='a',
        filename="bought.log",
        format="[%(asctime)s] [%(levelname)s] %(message)s"
    )
    log = logging.getLogger("bought")
    log.setLevel(logging.DEBUG)
    selenium_logger.setLevel(logging.WARNING)
    urllibLogger.setLevel(logging.WARNING)
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)

    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s",
                                "%Y-%m-%d %H:%M:%S")

    sh.setFormatter(formatter)
    log.addHandler(sh)

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
        log.info(f'Using FireFox webdriver.')
        if os.path.isdir(ctx.config["Main"]["BrowserProfile"]):
            log.info(f'Logging profile: {ctx.config["Main"]["BrowserProfile"]}')
            fp = webdriver.FirefoxProfile(ctx.config["Main"]["BrowserProfile"])
            log.info("Finished loading profile.")
        else:
            log.info("Using default blank profile.")

        options = webdriver.FirefoxOptions()
    elif drive == "chrome" or drive == "chromium":
        log.info(f'Using Chrome webdriver.')
        options = webdriver.ChromeOptions()
        if ctx.config["Main"]["BrowserProfile"]:
            log.info(f'Logging profile: {ctx.config["Main"]["BrowserProfile"]}')
            options.add_argument(f'--user-data-dir={ctx.config["Main"]["BrowserProfile"]}')
        else:
            log.info("Using default blank profile.")
    else:
        raise ValueError("Browser not specified!")

    if no_head:
        options.set_headless()
    options.page_load_strategy = "eager"

    if drive == "firefox":
        log.info("Starting webdriver.")
        driver = webdriver.Firefox(fp, firefox_options=options)
        log.info("Successfully created webdriver.")
    elif drive == "chrome" or drive == "chromium":
        driver = webdriver.Chrome(chrome_options=options)
    log.info("Setting implicit wait time.")
    driver.implicitly_wait(wait)
    ctx.obj["driver"] = driver

    if invoke_newegg:
        log.info("Starting Newegg script.")
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
