import lxml
import logging
from selenium import webdriver
import os

logging.basicConfig(filename='/var/log/updscripts.log', level=logging.DEBUG)
#Init selenium webdriver
webdriver = webdriver.PhantomJS(os.path.join(os.path.dirname(__file__),'bin/phantomjs'))

LOGIN_URL = 'https://www.rmoj.com/Account/Login'
MAIN_PAGE_URL = 'https://www.rmoj.com/membersonly/RigSpotter.aspx'


def Scrape():
    #Log in
    webdriver.

