from selenium import webdriver
from selenium.webdriver.firefox.options import Options, FirefoxProfile
import platform
from variables import WINDOWS_DRIVER, LINUX_DRIVER
import logging
import datetime
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def flatten(to_flat):
    """
    Flattens a list. From: [[a], [b], [c,d]] -> [a,b,c,d]
    :param to_flat:
    :return:
    """
    return [item for sublist in to_flat for item in sublist]


def cast_duples(tuples):
    """
    Cast the elements of a duple to int and str respectively.

    :param tuples:
    :param type_1:
    :param type_2:
    :return:
    """
    if len(tuples) == 0:
        return []
    assert len(tuples[0]) == 2
    return [(int(x[0]), str(x[1]).strip()) for x in tuples]


def find_all_indices(lst, item):
    """
    Finds the indices of item (even if duplicated)
    :param lst:
    :param item:
    :return:
    """
    return [i for i, x in enumerate(lst) if x == item]

def replace_nth_ocurrence(source, n, letter, new_value):
    """
    Replace the nth ocurrence from an array
    :param source: List of strings
    :param n: int
    :param letter: new value
    :param new_value: new value
    """
    ind = -1
    for i in range(n):
        ind = source.index(letter, ind+1)
    source[ind] = new_value
    return source


def fill_dict(array):
    """
    Fill a dictionary with default values.
    :param array: list
    """
    to_return = dict()
    none_list = ['actor', 'number', 'first_name', 'last_name']
    for i in array:
        to_return[i] = None if i in none_list else 0
    return to_return


def convert_time(time, period):
    try:
        period = int(period)
    except ValueError: # extra-time (only 5 minutes)
        period = int(period[1:])//2 + 4
    minutes, seconds = list(map(int, time.split(":")))
    seconds = 60 - seconds if seconds != 0 else 0
    minutes = 10*(period-1) + 9 - minutes if seconds != 0 else 10*(period-1) + 10 - minutes # carry
    return 60*minutes+seconds


def create_driver(driver_path):
    options = Options()
    options.headless = True
    #fp = webdriver.FirefoxProfile()
    #fp.set_preference("http.response.timeout", 30)
    #fp.set_preference("dom.max_script_run_time", 30)
    #driver = webdriver.Firefox(options=options, firefox_profile=fp, executable_path=chrome_driver_path)
    driver = webdriver.Firefox(options=options, executable_path=driver_path)
    driver.implicitly_wait(30)
    driver.set_page_load_timeout(300)

    return driver


def get_driver_path(driver_path=None):
    system = platform.system()
    if not driver_path:
        if system == "Linux":
            driver_path = LINUX_DRIVER
        elif system == "Windows":
            driver_path = WINDOWS_DRIVER
        else:
            print("ERROR: no --driverpath. When using a system different from Linux/Windows a driver path must be set")
            print("USAGE: --driverpath 'path/to/driver'")
            exit(-1)

        logger.info('No driver specified, using the system one by default ({})...\n'.format(driver_path))
    return driver_path


