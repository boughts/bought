"""
Main entry point for the bought command and application.
"""

import os
import sys
import json
import click
import logging
import pathlib
import subprocess
import configparser

from urllib3.connectionpool import log as urllibLogger
from selenium import webdriver
from selenium.webdriver.remote.remote_connection import LOGGER as selenium_logger
from bought.config import config_reader
from bought.websites.newegg import Newegg


def check():
    latest = subprocess.Popen(
        ["pip", "show", "bought"], stdout=subprocess.PIPE, shell=True
    )
    output = latest.stdout.read().decode("utf8")
    latest = output.split()[3]

    proc = subprocess.Popen(["bought", "--version"], stdout=subprocess.PIPE, shell=True)
    output = proc.stdout.read().decode("utf8")
    current = output.split()[2]
    return (latest, current)


@click.group(invoke_without_command=True, no_args_is_help=True)
@click.option(
    "-d",
    "--driver",
    type=click.Choice(["chrome", "chromium", "firefox"], case_sensitive=False),
    help="Run bought with the selected driver.",
)
@click.option(
    "-p",
    "--profile",
    "profile",
    help="Launch browser with this browser profile.",
)
@click.option(
    "-h",
    "--headless",
    is_flag=True,
    help="Run bought without a GUI.",
)
@click.option("--delay", default=4, help="Global delay value for restock check.")
@click.option(
    "--variance",
    default=1,
    help="Varies restock delay randomly in range of this amount range.",
)
@click.option("--wait", default=0, help="Global delay on all browser interactions.")
@click.option(
    "-t",
    "--testrun",
    is_flag=True,
    help="Run bought without making final purchase.",
)
@click.option(
    "-s",
    "--sound",
    is_flag=True,
    help="Play alert sounds on restock and order placement.",
)
@config_reader()
@click.version_option()
@click.pass_context
def main(ctx, driver, profile, headless, delay, variance, wait, testrun, sound):
    """A bot that purchases items online, rendering them bought.

    By default, bought uses the parameters specified in config.ini for
    configuration but these can also be specified via CLI.

    Made with <3 by jsonV
    """
    ctx.ensure_object(dict)
    ctx.obj["main"] = ctx.params

    drive = None
    fp = None
    no_head = False
    eager = False
    invoke_newegg = False
    wait = 0
    logging.basicConfig(
        filemode="a",
        filename="bought.log",
        format="[%(asctime)s] [%(levelname)s] %(message)s",
    )
    log = logging.getLogger("bought")
    log.setLevel(logging.DEBUG)
    selenium_logger.setLevel(logging.WARNING)
    urllibLogger.setLevel(logging.WARNING)
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    sh.setFormatter(formatter)
    log.addHandler(sh)

    latest, current = check()
    if latest > current:
        log.warn(
            f"You are running bought v{current}. Please upgrade to v{latest} with: 'pip install --upgrade bought'"
        )

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
        log.info(f"Using FireFox webdriver.")
        if ctx.config:
            if os.path.isdir(ctx.config["Main"]["BrowserProfile"]):
                log.info(f'Logging profile: {ctx.config["Main"]["BrowserProfile"]}')
                fp = webdriver.FirefoxProfile(ctx.config["Main"]["BrowserProfile"])
                log.info("Finished loading profile.")
            else:
                log.info("Using default blank profile.")

        options = webdriver.FirefoxOptions()
    elif drive == "chrome" or drive == "chromium":
        log.info(f"Using Chrome webdriver.")
        options = webdriver.ChromeOptions()
        if ctx.config:
            if ctx.config["Main"]["BrowserProfile"]:
                log.info(f'Logging profile: {ctx.config["Main"]["BrowserProfile"]}')
                options.add_argument(
                    f'--user-data-dir={ctx.config["Main"]["BrowserProfile"]}'
                )
            else:
                log.info("Using default blank profile.")

    if no_head:
        options.set_headless()

    if eager:
        options.page_load_strategy = "eager"

    if drive == "firefox":
        log.info("Starting webdriver.")
        driver = webdriver.Firefox(fp, firefox_options=options)
        log.info("Successfully created webdriver.")
    elif drive == "chrome" or drive == "chromium":
        log.info("Starting webdriver.")
        driver = webdriver.Chrome(chrome_options=options)
        log.info("Successfully created webdriver.")
    else:
        log.warn("No webdriver specified via config.ini or CLI!")
        log.warn(
            "Ensure config.ini specifies [Main][Driver] or CLI specifies driver via `bought -d firefox|chrome|chromium!"
        )

    if wait:
        log.info("Setting implicit wait time.")
        driver.implicitly_wait(wait)
    if drive:
        ctx.obj["driver"] = driver

    if invoke_newegg:
        log.info("Starting Newegg script.")
        ctx.obj["config"] = ctx.config
        ctx.invoke(newegg, items=items)


@main.command(no_args_is_help=True)
@click.option(
    "-i",
    "--items",
    default=[],
    required=True,
    help="A list of Newegg item numbers.",
)
@click.option("--delay", default=4, help="Newegg delay value for restock check.")
@click.option("-u", "--username", default="Username", help="Newegg email login.")
@click.option("-p", "--password", default="Password", help="Newegg password.")
@click.option(
    "--card", default="1234123412341234", help="Default Payment's Card number."
)
@click.option(
    "--cvv2", default="123", help="Default Payment's Card Verification Value."
)
@click.pass_context
def newegg(ctx, items, delay, username, password, card, cvv2):
    """Bought newegg items."""
    newegg = Newegg(ctx.obj, items, delay, username, password, card, cvv2)
    newegg.bought()
