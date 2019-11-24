from selenium import webdriver
from selenium.webdriver.firefox.options import Options, FirefoxProfile
import platform
import logging
import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


def get_driver_path(driver_path):
    system = platform.system()
    if not driver_path:
        if system == "Linux":
            driver_path = "./geckodriver_linux"
        elif system == "Windows":
            driver_path = "./geckodriver_windows"
        else:
            print("ERROR: no --driverpath. When using a system different from Linux/Windows a driver path must be set")
            print("USAGE: --driverpath 'path/to/driver'")
            exit(-1)

        logger.info('No driver specified, using the system one by default ({})...\n'.format(driver_path))
    return driver_path


def get_current_season():

    #We take te current time
    now = datetime.datetime.now()
    #We extract the current year and the current month
    current_year = now.year
    current_month=now.month

    #We check if the current_month is bewteen January and July. We need to know the real year of the current season
    if current_month >= 1 & current_month <8:
        real_current_year=current_year-1
    #otherwise the real_current_year is equal to the current year because we are between august and december
    else:
        real_current_year=current_year


    real_next_year = real_current_year + 1

    #we set the first day of the current season and the last day of the current season
    first_day_current_season = datetime.datetime(real_current_year, 9, 1)
    last_day_current_season = datetime.datetime(real_next_year, 8, 1)

    if first_day_current_season < now < last_day_current_season:
        current_season = real_current_year
    else:
        current_season = now.year + 1

    return current_season