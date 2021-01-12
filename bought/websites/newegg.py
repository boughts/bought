import os
import sys
import time
import math
import click
import random
import logging
import datetime
import requests

from bought.sounds.play import play
from threading import Thread
from lxml import html
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementNotInteractableException,
    ElementClickInterceptedException,
    TimeoutException,
)

__all__ = ["Newegg"]


class Newegg:
    def __init__(self, obj, items, delay, username, password, card, cvv2):
        self.obj = obj
        self.items = [item.strip() for item in items.split(",")]
        self.delay = delay
        self.username = username
        self.password = password
        self.card = card
        self.cvv2 = cvv2
        self.driver = obj["driver"]
        self.base_url = "https://www.newegg.com/"
        self.sign_in = ["Sign in / Register", "Sign In"]
        self.tabs = {}
        self.log = logging.getLogger("bought")

        try:
            if self.obj["main"]:
                main_delay_variance = float(self.obj["main"]["variance"])
                self.delay_lower = self.delay - main_delay_variance
                assert self.delay_lower > 0
                self.delay_upper = self.delay + main_delay_variance
            if self.obj.config:
                self.config = obj["config"]
                newegg_delay = self.config["Newegg"]["Delay"]
                main_delay = self.config["Main"]["Delay"]
                self.delay = float(newegg_delay if newegg_delay else main_delay)
                main_delay_variance = float(self.config["Main"]["DelayVariance"])
                self.delay_lower = self.delay - main_delay_variance
                assert self.delay_lower > 0
                self.delay_upper = self.delay + main_delay_variance
                self.username = self.config["Newegg"]["Username"]
                self.password = self.config["Newegg"]["Password"]
                self.card = self.config["Newegg"]["Card"]
                self.cvv2 = self.config["Newegg"]["CVV2"]
                self.items = [item.strip() for item in items.split(",")]
        except:
            pass
        try:
            assert self.items != []
        except:
            self.log.warn("No items specified. Exiting...")
            self.driver.close()
            sys.exit()

        self.log.info(f"Newegg items to monitor: {self.items}")

    def close_popup(self):
        """Closes the popup sale that appears on the landing page."""
        try:
            popup = self.driver.find_element_by_id("popup-close")
            self.log.debug("Closing popup.")
            if popup:
                popup.click()
        except NoSuchElementException:
            pass
        except ElementNotInteractableException:
            pass

    def find_items(self):
        """Opens the products pages in new tabs to prepare for stock
        checking"""
        self.log.info("Opening tabs...")
        self.close_popup()
        item_iter = iter(self.items)
        while True:
            try:
                item = next(item_iter)
                self.driver.execute_script(
                    f"window.open('{self.base_url}/p/{item}', '{item}')"
                )
                self.log.info(f"Opening {item}")
                self.tabs[item] = self.driver.window_handles[-1]
                self.log.info(f"window handles: {self.driver.window_handles}")
                self.log.info(f"Adding tab: {self.tabs}")
                time.sleep(random.uniform(self.delay_lower, self.delay_upper))
            except StopIteration:
                self.log.info("All item tabs opened.")
                break

    def log_in(self):
        self.close_popup()
        xpath = '//a[@class="nav-complex-inner"]'
        try:
            self.driver.find_element_by_xpath(xpath).click()
        except NoSuchElementException:
            pass
        if self.username and self.password:
            try:
                self.log.info("Looking for E-Mail field.")
                username_input = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "labeled-input-signEmail"))
                )
                username_input.send_keys(self.username)
                self.log.info("Clicking Sign In Button.")
                sign_in_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "signInSubmit"))
                )
                sign_in_btn.click()
                try:
                    invalid_email = WebDriverWait(self.driver, 1).until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                "/html/body/div[5]/div/div[2]/div/div/div[1]/form/div/div[1]/div/div",
                            )
                        )
                    )
                    self.log.warn("Invalid email entered.")
                    raise SystemExit
                except SystemExit:
                    self.log.warn("Exiting...")
                    self.driver.close()
                    sys.exit()
                except:
                    pass
                while True:
                    try:
                        WebDriverWait(self.driver, 1).until(
                            EC.element_to_be_clickable(
                                (By.ID, "labeled-input-signEmail")
                            )
                        )
                    except:
                        break

                try:
                    self.log.info("Checking if security code sent.")
                    security_code = WebDriverWait(self.driver, 1).until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                "/html/body/div[5]/div/div[2]/div/div/div[3]/form/div/div[2]/div",
                            )
                        )
                    )
                    self.log.debug("Security code prompted.")
                    self.log.debug(
                        "Waiting until you type in security code and move to next page."
                    )
                    while True:
                        try:
                            if self.driver.find_element_by_xpath(xpath):
                                return
                        except:
                            pass
                except:
                    self.log.info("No security code sent.")
                self.log.info("Looking for password field.")
                password_input = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "labeled-input-password"))
                )
                self.log.info("Entering password field.")
                password_input.send_keys(self.password)
                self.log.info("Submitting password.")
                self.driver.find_element_by_xpath(
                    '//div[@class="form-cell"][3]'
                ).click()
            except Exception as e:
                self.log.warn(f"{e}")
                self.log.warn("Exiting...")
                self.driver.close()
                sys.exit()
        else:  # Username and password not provided
            while self.driver.find_element_by_id("labeled-input-signEmail"):
                self.log.debug(
                    "Waiting 15 seconds for you to signin (user and password)."
                )
                time.sleep(15)

    def is_logged_in(self):
        self.close_popup()
        xpath = '//div[@class="nav-complex-title"]'
        try:
            self.log.info("Checking if logged in...")
            signin = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.ID, "labeled-input-signEmail"))
            )
            self.log.debug("On login screen. Not logged in...")
            return False
        except Exception as e:
            try:
                if self.driver.find_element_by_xpath(xpath).text in self.sign_in:
                    self.log.info("On landing page. Not logged in...")
                    return False
            except:
                pass
        self.log.info("Already logged in on landing page!")
        return True

    def add_to_cart(self):

        # Play sound in new thread
        if self.config["Main"]["PlaySound"].lower() == "true":
            self.log.info("Playing alert sound.")
            success_alert = Thread(target=play, args=("bought/sounds/alert.mp3",))
            success_alert.start()

        # Protection plan
        try:
            xpath = '//button[@class="btn"]'
            self.log.info("Checking if protection plan available.")
            btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            if btn.text.lower() == "no, thanks":
                self.log.info("Protection Plan: No, thanks.")
                btn.click()
        except NoSuchElementException as e:
            self.log.warn(f"Error {e}")
        except ElementNotInteractableException as e:
            self.log.warn(f"Error {e}")

        # View Cart & Checkout
        try:
            self.log.info("View cart/checkout")
            xpath1 = '//button[@class="btn btn-undefined btn-primary"]'
            self.driver.find_element_by_xpath(xpath1).click()
        except NoSuchElementException as e:
            self.log.warn(f"Error {e}")

        # Secure Checkout
        try:
            xpath2 = '//button[@class="btn btn-primary btn-wide"]'
            self.driver.find_element_by_xpath(xpath2).click()
            self.log.info("Clicked Secure Checkout.")
        except NoSuchElementException as e:
            self.log.warn(f"Error {e}")
        except ElementClickInterceptedException as e:
            self.driver.find_element_by_xpath(
                "/html/body/div[8]/div[1]/div/div/div/div[3]/div[2]/button[1]"
            ).click()

    def check_stock(self):
        """Cycles through opened tabs, refreshes, check if product is restocked."""
        add_to_cart_btn = '//button[@class="btn btn-primary btn-wide"]'
        human = "/html/body/div[1]/div[2]/h1"
        self.log.info(f"Cycling through tabs: {self.tabs}")
        while True:
            self.log.info("Refreshing page(s) in background...")
            for tab in self.tabs.keys():
                try:
                    result = requests.get(f"https://www.newegg.com/p/{tab}")
                    result.raise_for_status()
                    tree = html.fromstring(result.text)
                    if tree.xpath(add_to_cart_btn):
                        self.log.info(f"{tab} IN STOCK!")
                        self.driver.switch_to.window(self.tabs[tab])
                        self.driver.refresh()
                        add_to_cart = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, add_to_cart_btn))
                        )
                        add_to_cart.click()
                        self.log.info(f"Clicked ADD TO CART.")
                        return
                    elif tree.xpath(human):
                        self.log.warn(
                            "Newegg is asking if you're a bot. Human interaction required!"
                        )
                        self.driver.switch_to.window(self.tabs[tab])
                        self.driver.refresh()
                        while True:
                            try:
                                human = WebDriverWait(self.driver, 10).until(
                                    EC.element_to_be_clickable((By.XPATH, human))
                                )
                            except:
                                self.log.info("You are human!")
                                break

                    self.log.info(f"{tab} not in stock...")
                except Exception as e:
                    self.log.warn(f"Error loading webpage:{str(e)}")

            time.sleep(random.uniform(self.delay_lower, self.delay_upper))

    def purchase(self):
        self.log.debug("Purchasing...")
        try:
            self.log.debug("Typing CVV.")
            cvv2_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/div[7]/div/section/div/div/form/div[2]/div[1]/div/div[3]/div/div[2]/div[1]/div[2]/div[3]/input",
                    )
                )
            )
            a = ActionChains(self.driver)
            a.click_and_hold(cvv2_input).move_by_offset(100, 100).release().perform()
            cvv2_input.send_keys(self.cvv2)
            self.log.debug("Clicking Place Order")
            place_order_btn = self.driver.find_element_by_xpath(
                '//*[@id="btnCreditCard"]'
            )
            if self.config["Main"]["Testrun"].lower() == "true":
                return
            place_order_btn.click()
            self.log.debug("Order completed!")

        except Exception as e:
            self.log.warn(e)
            self.log.warn(f"Couldn't auto purchase. Exiting...")
            sys.exit()

    def are_you_human(self):
        """https://www.newegg.com/areyouahuman?itn=true&referer=/areyouahuman?referer=https%3A%2F%2Fwww.newegg.com%2F&why=8"""
        checkbox = "/html/body/div[2]/div[3]/div[1]/div/div/span/div[1]"
        try:
            self.driver.find_element_by_xpath(checkbox).click()
        except:
            pass

    def bought(self):
        """Performs a sequence of purchasing operations."""
        # Go to NewEgg's website
        self.log.info(f"Opening webpage: {self.base_url}.")
        self.driver.get(self.base_url)

        # Check if you are banned
        ban_xpath = '//div[@class="page-404-text"]'
        try:
            if self.driver.find_element_by_xpath(ban_xpath):
                self.log.warn("You are currently proxy banned! Exiting...")
                self.log.warn("Try increasing the Newegg Delay value.")
                exit()
        except Exception:
            pass

        # Ensure self.log.ed in before continuing
        while not self.is_logged_in():
            self.log_in()
            time.sleep(random.uniform(self.delay_lower, self.delay_upper))

        # Open tabs
        self.find_items()

        # Refresh pages until not sold out - adds first to restocked item to cart.
        self.check_stock()

        # Clicks secure checkout
        self.add_to_cart()

        # Sign in if necessary
        while not self.is_logged_in():
            time.sleep(random.uniform(self.delay_lower, self.delay_upper))
            self.log_in()

        # Place order screen
        self.purchase()

        # If all has gone well...
        self.log.info("Congrats!")
        if self.config["Main"]["PlaySound"].lower() == "true":
            success_alert = Thread(target=play, args=("bought/sounds/success.mp3",))
            success_alert.start()
