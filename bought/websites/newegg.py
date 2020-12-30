import os
import time
import math
import click
import random
import logging
import datetime
import requests

from bought.sounds.play import play
from threading import Thread

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
    def __init__(self, obj, items):
        self.obj = obj
        self.config = obj["config"]
        self.driver = obj["driver"]
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
        self.base_url = "https://www.newegg.com/"
        self.items = [item.strip() for item in items.split(",")]
        self.sign_in = ["Sign in / Register", "Sign In"]
        self.tabs = {}
        self.log = logging.getLogger("bought")
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
                self.tabs[item] = self.driver.window_handles[1]
                time.sleep(random.uniform(self.delay_lower, self.delay_upper))
            except StopIteration:
                self.log.info("All item tabs opened.")
                break

    def log_in(self):
        time.sleep(2)
        self.close_popup()
        xpath = '//a[@class="nav-complex-inner"]'
        try:
            self.driver.find_element_by_xpath(xpath).click()
        except NoSuchElementException:
            pass
        if self.username and self.password:
            time.sleep(2)
            username_input = self.driver.find_element_by_id("labeled-input-signEmail")
            username_input.send_keys(self.username)
            try:
                sign_in_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//div[@class='form-cell'][3]"
                        )
                    )
                )
                sign_in_btn.click()
            except:
                exit()
            try:
                self.log.debug("Getting security code.")
                security_code = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            "/html/body/div[5]/div/div[2]/div/div/div[3]/form/div/div[2]/div",
                        )
                    )
                )
                if security_code.text == "Enter the code that has been sent to":
                    self.log.debug("Waiting until you type in security code and move to next page.")
                    while True:
                        try:
                            if self.driver.find_element_by_xpath(xpath):
                                return
                        except:
                            pass
            except:
                pass
            password_input = self.driver.find_element_by_id("labeled-input-password")
            password_input.send_keys(self.password)
            self.driver.find_element_by_xpath('//div[@class="form-cell"][3]').click()
        else:  # Username and password not provided
            while self.driver.find_element_by_id("labeled-input-signEmail"):
                self.log.debug("Waiting 15 seconds for you to signin (user and password).")
                time.sleep(15)

    def is_logged_in(self):
        self.close_popup()
        xpath = '//div[@class="nav-complex-title"]'
        xpath2 = '//div[@class="signin-body"]'
        try:
            if self.driver.find_element_by_xpath(xpath).text in self.sign_in:
                self.log.debug("Not logged in. 'Sign in / Register' text visible on homepage.")
                return False
        except NoSuchElementException:
            try:
                if self.driver.find_element_by_xpath(xpath2).text in self.sign_in:
                    self.log.debug("Not logged in. On 'Sign In' page.")
                    return False
            except NoSuchElementException:
                pass
        self.log.debug("Already logged in on landing page!")
        return True

    def add_to_cart(self):

        # Play sound in new thread
        if self.config["Main"]["PlaySound"].lower() == "true":
            success_alert = Thread(target=play, args=("bought/sounds/alert.mp3",))
            success_alert.start()

        # Protection plan
        try:
            self.log.debug("No protection plan.")
            xpath = '//button[@class="btn"]'
            btn = self.driver.find_element_by_xpath(xpath)
            if btn.text == "No, thanks":
                btn.click()
        except NoSuchElementException as e:
            self.log.warn(f"Error {e}")
        except ElementNotInteractableException as e:
            self.log.warn(f"Error {e}")

        # View Cart & Checkout
        try:
            self.log.debug("View cart/checkout")
            xpath1 = '//button[@class="btn btn-undefined btn-primary"]'
            self.driver.find_element_by_xpath(xpath1).click()
        except NoSuchElementException as e:
            self.log.warn(f"Error {e}")

        # Secure Checkout
        try:
            self.log.debug("Secure checkout.")
            xpath2 = '//button[@class="btn btn-primary btn-wide"]'
            self.driver.find_element_by_xpath(xpath2).click()
        except NoSuchElementException as e:
            self.log.warn(f"Error {e}")
        except ElementClickInterceptedException as e:
            self.driver.find_element_by_xpath(
                "/html/body/div[8]/div[1]/div/div/div/div[3]/div[2]/button[1]"
            ).click()

    def secure_checkout(self):

        if not self.is_logged_in():
            self.log_in()

        # Enter CVV2
        try:
            self.log.debug("Entering CVV2 and Review Order")
            time.sleep(1)
            cvv2_input = self.driver.find_element_by_xpath(
                "/html/body/div[7]/div/section/div/div/form/div[2]/div[1]/div/div[3]/div/div[2]/div[1]/div[2]/div[3]/input"
            )
            cvv2_input.click()
            a = ActionChains(self.driver)
            a.click_and_hold(cvv2_input).move_by_offset(-100, -100).release().perform()
            cvv2_input.send_keys(self.cvv2)
        except Exception as e:
            self.log.warn(f"Error {e}")

        try:
            place_order_btn = self.driver.find_element_by_xpath(
                '//*[@id="btnCreditCard"]'
            )
            place_order_btn.click()

        except ElementClickInterceptedException:
            # Continue to Payment
            try:
                self.log.debug("Continue to Payment.")
                continue_to_payment_btn_path = "/html/body/div[7]/div/section/div/div/form/div[2]/div[1]/div/div[2]/div/div[3]/button"
                payment = self.driver.find_element_by_xpath(
                    continue_to_payment_btn_path
                )
                last_height = self.driver.execute_script(
                    "return document.body.scrollHeight"
                )
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )
                ActionChains(self.driver).move_to_element(payment).click().perform()

            except NoSuchElementException as e:
                self.log.warn(f"Error {e}")

            # Review your Order
            try:
                xpath4 = "/html/body/div[7]/div/section/div/div/form/div[2]/div[1]/div/div[3]/div/div[3]/button"
                self.driver.find_element_by_xpath(xpath4).click()
            except NoSuchElementException as e:
                self.log.warn(f"Error {e}")
            except ElementNotInteractableException as e:
                self.log.warn(f"Error {e}")

            # Retype Card Number
            try:
                self.log.debug("Typing Card Number...")
                self.driver.switch_to.frame(
                    self.driver.find_element_by_tag_name("iframe")
                )
                card_inp = self.driver.find_element_by_xpath(
                    "/html/body/div[6]/div/div[2]/div[2]/div[1]/input"
                )
                a = ActionChains(self.driver)
                a.click_and_hold(card_inp).move_by_offset(10, 10).release().perform()
                card_inp.send_keys(self.card)
                save_button = "/html/body/div[6]/div/div[3]/button[2]"
                self.driver.find_element_by_xpath(save_button).click()
                self.driver.switch_to.default_content()
            except NoSuchElementException:
                self.driver.switch_to.default_content()
            except ElementClickInterceptedException:
                self.driver.switch_to.default_content()

        finally:
            place_order_btn = self.driver.find_element_by_xpath(
                '//*[@id="btnCreditCard"]'
            )
            place_order_btn.click()

    def check_stock(self):
        """Cycles through opened tabs, refreshes, check if product is restocked."""
        add_to_cart_btn = '//button[@class="btn btn-primary btn-wide"]'
        while True:
            self.log.info("Refreshing page(s)...")
            for tab in self.tabs.keys():
                WebDriverWait(self.driver, 3).until(
                    EC.number_of_windows_to_be(len(self.tabs.keys()) + 1)
                )
                self.driver.switch_to.window(self.tabs[tab])
                self.driver.refresh()
                try:
                    if self.driver.find_element_by_xpath(add_to_cart_btn):
                        self.log.info(f"{tab} IN STOCK!")
                        return self.driver.find_element_by_xpath(add_to_cart_btn).click()
                except NoSuchElementException:
                    self.log.info(f"{tab} NOT in stock...")
                    pass
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

        except TimeoutException:
            exit()

        except Exception as e:
            self.log.warn(f"Couldn't auto purchase. {e}\nExiting...")
            exit()

    def are_you_human(self):
        '''https://www.newegg.com/areyouahuman?itn=true&referer=/areyouahuman?referer=https%3A%2F%2Fwww.newegg.com%2F&why=8'''
        checkbox = ('/html/body/div[2]/div[3]/div[1]/div/div/span/div[1]')
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
                self.log.warn("Try increasing the Main.Delay value.")
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

        # Secure checkout -> Sign in if necessary -> Continue to Payment, enter CVV2
        self.add_to_cart()

        # Place order screen
        self.purchase()

        # If all has gone well...
        self.log.info("Congrats!")
        if self.config["Main"]["PlaySound"].lower() == "true":
            success_alert = Thread(target=play, args=("bought/sounds/success.mp3",))
            success_alert.start()
