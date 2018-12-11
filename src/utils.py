from selenium import webdriver
from selenium.webdriver.firefox.options import Options, FirefoxProfile

def replace_nth_ocurrence(source, n, letter, new_value):
    """
    Replace the nth ocurrence from an array
    :param source: String
    :param n: int
    :param letter: new value
    :param new_value: new value
    """
    ind = source.index(letter, n)
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
