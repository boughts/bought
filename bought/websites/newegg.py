import os
import time
import math
import click
import random
import datetime
import requests

from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException, ElementClickInterceptedException

__all__ = [
    "Newegg"
]

class Newegg():
    def __init__(self, obj, items):
        self.obj = obj
        self.config = obj['config']
        self.driver = obj['driver']
        newegg_delay = self.config['Newegg']['Delay']
        main_delay = self.config['Main']['Delay']
        self.delay = float(newegg_delay if newegg_delay else main_delay)
        main_delay_variance = float(self.config['Main']['DelayVariance'])
        self.delay_lower = self.delay - main_delay_variance
        self.delay_upper = self.delay + main_delay_variance
        self.username = self.config['Newegg']['Username']
        self.password = self.config['Newegg']['Password']
        self.card = self.config['Newegg']['Card']
        self.cvv2 = self.config['Newegg']['CVV2']
        self.base_url = "https://www.newegg.com/"
        self.items = [item.strip() for item in items.split(',')]
        self.sign_in = [
            "Sign in / Register",
            "Sign In"
        ]
        self.tabs = {}

    def close_popup(self):
        '''Closes the popup sale that appears on the landing page.'''
        try:
            popup = self.driver.find_element_by_id("popup-close")
            if popup:
                popup.click()
        except NoSuchElementException:
            pass
        except ElementNotInteractableException:
            pass

    def find_items(self):
        '''Opens the products pages in new tabs to prepare for stock
        checking'''
        self.close_popup()
        item_iter = iter(self.items)
        while True:
            try:
                item = next(item_iter)
                self.driver.execute_script(f"window.open('{self.base_url}/p/{item}', '{item}')")
                self.tabs[item] = self.driver.window_handles[1]
                time.sleep(random.uniform(self.delay_lower, self.delay_upper))
            except StopIteration:
                break
    
    def log_in(self):
        time.sleep(2)
        self.close_popup()
        xpath = ('//a[@class="nav-complex-inner"]')
        try:
            self.driver.find_element_by_xpath(xpath).click()
        except NoSuchElementException:
            pass
        if self.username and self.password:
            username_input = self.driver.find_element_by_id('labeled-input-signEmail')
            username_input.send_keys(self.username)
            time.sleep(2)
            self.driver.find_element_by_xpath('//div[@class="form-cell"][3]').click()
            time.sleep(2)
            password_input = self.driver.find_element_by_id('labeled-input-password')
            password_input.send_keys(self.password)
            time.sleep(2)
            self.driver.find_element_by_xpath('//div[@class="form-cell"][3]').click()
        else: # Username and password not provided
            while(self.driver.find_element_by_id('labeled-input-signEmail')):
                print("Waiting 15 seconds for you to signin (user and password).")
                time.sleep(15)

    def is_logged_in(self):
        self.close_popup()
        xpath = ('//div[@class="nav-complex-title"]')
        xpath2 = ('//div[@class="signin-body"]')
        try:
            if self.driver.find_element_by_xpath(xpath).text in self.sign_in:
                return False
        except NoSuchElementException as e:
            print(e)
        
        try:
            if self.driver.find_element_by_xpath(xpath2).text in self.sign_in:
                return False
        except NoSuchElementException as e:
            print(e)
        return True

    def add_to_cart(self):
        # Protection plan
        while True:
            try:
                print("Protection plan")
                xpath = ('//button[@class="btn"]')
                self.driver.find_element_by_xpath(xpath).click()
                break
            except NoSuchElementException as e:
                time.sleep(.001)
                print(e)
            except ElementNotInteractableException as e:
                time.sleep(.001)
                print(e)

        # View Cart & Checkout
        try:
            print("View cart/checkout")
            xpath1 = ('//button[@class="btn btn-undefined btn-primary"]')
            self.driver.find_element_by_xpath(xpath1).click()
        except NoSuchElementException as e:
            print(e)

        # Secure Checkout
        try:
            print("Secure checkout")
            xpath2 = ('//button[@class="btn btn-primary btn-wide"]')
            self.driver.find_element_by_xpath(xpath2).click()
        except NoSuchElementException as e:
            print(e)

        # Enter CVV2
        try:
            print("Entering CVV2 and Review Order")
            time.sleep(1)
            cvv2_input = self.driver.find_element_by_xpath('/html/body/div[7]/div/section/div/div/form/div[2]/div[1]/div/div[3]/div/div[2]/div[1]/div[2]/div[3]/input')
            cvv2_input.click()
            a = ActionChains(self.driver)
            a.click_and_hold(cvv2_input).move_by_offset(-100,-100).release().perform()
            cvv2_input.send_keys(self.cvv2)
        except Exception as e:
            print(f"{e}: Trying again...")

        try:
            place_order_btn = self.driver.find_element_by_xpath('//*[@id="btnCreditCard"]')
            place_order_btn.click()

        except ElementClickInterceptedException:
            # Continue to Payment
            while True:
                try:
                    print("Continue to Payment")
                    xpath3 = ('/html/body/div[7]/div/section/div/div/form/div[2]/div[1]/div/div[2]/div/div[3]/button')
                    payment = self.driver.find_element_by_xpath(xpath3)
                    print(payment)
                    last_height = self.driver.execute_script("return document.body.scrollHeight")
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    ActionChains(self.driver).move_to_element(payment).click().perform()
                    break
                except NoSuchElementException as e:
                    print(f"{e}: Trying again...")
                    time.sleep(.1)
                    pass

            # Review your Order 
            while True:
                try:
                    xpath4 = ('/html/body/div[7]/div/section/div/div/form/div[2]/div[1]/div/div[3]/div/div[3]/button')
                    self.driver.find_element_by_xpath(xpath4).click()
                    break
                except NoSuchElementException as e:
                    print(f"{e}: Trying again...")
                    pass
                except ElementNotInteractableException as e:
                    print(f"{e}: Trying again...")
                    pass

            # Retype Card Number
            while True:
                try:
                    print("Typing Card Number")
                    self.driver.switch_to.frame(self.driver.find_element_by_tag_name("iframe"))
                    card_inp = self.driver.find_element_by_xpath('/html/body/div[6]/div/div[2]/div[2]/div[1]/input')
                    card_inp.click()
                    a = ActionChains(self.driver)
                    a.click_and_hold(card_inp).move_by_offset(10,10).release().perform()
                    card_inp.send_keys(self.card)
                    save_button = ('/html/body/div[6]/div/div[3]/button[2]')
                    self.driver.find_element_by_xpath(save_button).click()
                    self.driver.switch_to.default_content()
                    break
                except NoSuchElementException:
                    self.driver.switch_to.default_content()
                except ElementClickInterceptedException:
                    self.driver.switch_to.default_content()
        
        finally:
            place_order_btn = self.driver.find_element_by_xpath('//*[@id="btnCreditCard"]')
            place_order_btn.click()


    def check_stock(self):
        '''Cycles through opened tabs, refreshes, check if product is restocked.
        '''
        xpath = ('//button[@class="btn btn-primary btn-wide"]')
        while True:
            for tab in self.tabs.keys():
                WebDriverWait(self.driver, 3).until(EC.number_of_windows_to_be( len(self.tabs.keys()) + 1 ))
                self.driver.switch_to.window(self.tabs[tab])
                self.driver.refresh()
                try:
                    if self.driver.find_element_by_xpath(xpath):
                        self.driver.find_element_by_xpath(xpath).click()
                        self.add_to_cart()
                        return tab
                except NoSuchElementException:
                    pass
            time.sleep(random.uniform(self.delay_lower, self.delay_upper))

    def bought(self):
        '''Performs a sequence of purchasing operations.
        '''
        # Go to NewEgg's website
        self.driver.get(self.base_url)
        time.sleep(3)
        # Ensure logged in before continuing
        while not self.is_logged_in():
            print("Not logged in! Attempting auto-login...")
            self.log_in()
            time.sleep(random.uniform(self.delay_lower, self.delay_upper))

        # Open tabs
        self.find_items()

        # Refresh pages until not sold out - adds first to restocked item to cart. 
        self.check_stock()

        # Secure checkout -> Sign in if necessary -> Continue to Payment, enter CVV2

        # See place order screen, stop script.
        self.driver.find_element_by_xpath('//*[@id="btnCreditCard"]').click()
        print("Congrats")
