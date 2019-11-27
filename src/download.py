import requests
import os
import logging
import urllib.request
from pyquery import PyQuery as pq
from src.utils import create_driver
import os
import time
from src.utils import logger
from requests import Session
from PIL import Image
from io import BytesIO


class File:
    def __init__(self, path):
        self.path = path
        self.extension = self._get_extension()
        self.type = self._get_type()

    def _get_extension(self):
        return self.path.split('.')[-1]

    def _get_type(self):
        if self.extension == 'html':
            return 'text'
        elif self.extension in ['jpg', 'jpeg', 'png', 'gif']:
            return 'image'
        else:
            raise NotImplementedError

    def exists(self):
        return os.path.isfile(self.path)

    def open(self):
        if self.type == 'text':
            with open(self.path, 'r', encoding="utf-8") as f:
                return f.read()
        elif self.type == 'image':
            return self.path
        return

    def download(self, url, download_manager):
        r = download_manager.session.get(url)
        try:
            r.raise_for_status()
            if self.type == 'text':
                with open(self.path, 'w', encoding="utf-8") as f:
                    f.write(r.text)
                return r.text
            elif self.type == 'image':
                i = Image.open(BytesIO(r.content))
                i.save(self.path)
                return self.path
        except requests.exceptions.HTTPError as e:
            logger.warning(e)
        return

    def open_or_download(self, url=None, download_manager=None):
        """
        Open or download a file.

        :param filepath: String
        :param url: String
        :return: content of the file.
        """
        if self.exists():
            return self.open()
        elif url:
            return self.download(url=url, download_manager=download_manager)
        else:
            raise FileNotFoundError(self.path)



class DownloadManager:
    def __init__(self):
        self.session = Session()

    def send_request(self, url):
        self.session.get(url)

    # def open_or_download(self, filepath, url=None):

    #
    # def get_page(self, url):
    #     """
    #     Get data from URL.
    #
    #     :param url: String
    #     :return: content of the page
    #     """
    #
    #

        #     return content
        # except Exception as e:
        #     logger.error("Fail to download url: {}".format(url))
        #     logger.error("Error: {}".format(e), exc_info=True)
        #     exit(-1)

    # def save_content(self, file_path, content):
    #     """
    #     Saves the content to a file in the path provided.
    #
    #     :param file_path: String
    #     :param content: String
    #     :return: content of the page
    #     """
    #     with open(file_path, 'w', encoding="utf-8") as file:
    #         file.write(content)
    #         return content

    # def open_or_download(self, file_path, url=None):
    #     """
    #     Open or download a file.
    #
    #     :param file_path: String
    #     :param url: String
    #     :return: content of the file.
    #     """
    #
    #     if os.path.isfile(file_path):
    #         with open(file_path, 'r', encoding="utf-8") as file:
    #             return file.read()
    #     elif url:
    #         html_file = self.get_page(url)
    #         return self.save_content(file_path, html_file)
    #     else:
    #         raise FileNotFoundError(file_path)
    #
    # def open_or_download_photo(self, file_path, url=None):
    #     if os.path.isfile(file_path):
    #         return file_path
    #     elif url:
    #         r = self.session.get(url)
    #         i = Image.open(BytesIO(r.content))
    #         i.save(file_path)
    #         # try:
    #         #     urllib.request.urlretrieve(url, file_path)
    #         # except urllib.request.HTTPError as e:
    #         #     logger.error('Error downloading image: {}'.format(url))
    #         #     logger.error(e)
    #     else:
    #         raise FileNotFoundError(file_path)

#
# def download(file_path, url):
#     """
#     Open or download a file.
#
#     :param file_path: String
#     :param url: String
#     :return: content of the file.
#     """
#     if os.path.isfile(file_path):
#         os.remove(file_path)
#         html_file = get_page(url)
#         return save_content(file_path, html_file)
#     else:
#         html_file = get_page(url)
#         return save_content(file_path, html_file)



#
# def sanity_check(directory_name, logging_level=logging.INFO):
#     """
#     Checks if thes file within a directoy have been correctly downloaded
#
#     :param directory_name: String
#     :param logging_level: logging object
#     """
#     logging.basicConfig(level=logging_level)
#     logger = logging.getLogger(__name__)
#
#     errors = []
#     directory = os.fsencode(directory_name)
#     for file in os.listdir(directory):
#         with open(os.path.join(directory, file), encoding="utf-8") as f:
#             try:
#                 raw_html = f.read()
#
#                 doc = pq(raw_html)
#                 if doc("title").text() == '404 Not Found':
#                     errors.append(os.fsdecode(file))
#             except:
#                 pass
#
#     if errors: raise Exception('There are {} errors in the downloads!'.format(len(errors)))
#     logger.info('Sanity check of {} correctly finished!\n'.format(os.fsdecode(directory)))
#     return errors
#
#
# def sanity_check_game(directory_name, logging_level=logging.INFO):
#     """
#     Checks if thes file within a directoy have been correctly downloaded
#
#     :param directory_name: String
#     :param logging_level: logging object
#     """
#     logging.basicConfig(level=logging_level)
#     logger = logging.getLogger(__name__)
#
#     errors = []
#     directory = os.fsencode(directory_name)
#     for file in [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]:
#         with open(os.path.join(directory, file), encoding="utf-8") as f:
#             raw_html = f.read()
#
#             doc = pq(raw_html)
#             if doc("title").text() == '404 Not Found':
#                 errors.append(os.fsdecode(file))
#
#             filename=file.decode("utf-8")
#             statinfo2=os.stat(directory_name+filename)
#             f.close()
#             if statinfo2.st_size < 20000:
#                 logger.info('The game ' + filename +' data is not correct. Missing data. Deleting game html...')
#                 try:
#                     os.remove(directory_name+filename)
#                     logger.info('game ' + filename + ' deleted...')
#                     continue
#
#                 except:
#                     logger.info('game ' + filename + ' cannot be deleted...')
#
#     if errors:
#         raise Exception('There were {} errors in the downloads!'.format(len(errors)))
#
#     logger.info('Sanity check of {} correctly finished!\n'.format(os.fsdecode(directory)))
#     return errors
#
#
# def sanity_check_game_copa(directory_name, logging_level=logging.INFO):
#     """
#     Checks if thes file within a directoy have been correctly downloaded
#
#     :param directory_name: String
#     :param logging_level: logging object
#     """
#     logging.basicConfig(level=logging_level)
#     logger = logging.getLogger(__name__)
#
#     errors = []
#     directory = os.fsencode(directory_name)
#     for file in os.listdir(directory):
#         with open(os.path.join(directory, file), encoding="utf-8") as f:
#             raw_html = f.read()
#
#             doc = pq(raw_html)
#             if doc("title").text() == '404 Not Found':
#                 errors.append(os.fsdecode(file))
#
#             filename=file.decode("utf-8")
#             statinfo2=os.stat(directory_name+filename)
#             f.close()
#             if statinfo2.st_size < 20000:
#                 logger.info('The game ' + filename +' data is not correct. Missing data. Deleting game html...')
#                 try:
#                     os.remove(directory_name+filename)
#                     logger.info('game ' + filename + ' deleted...')
#                     continue
#
#                 except:
#                     logger.info('game ' + filename + ' cannot be deleted...')
#
#     if errors:
#         raise Exception('There were {} errors in the downloads!'.format(len(errors)))
#
#     logger.info('Sanity check of {} correctly finished!\n'.format(os.fsdecode(directory)))
#     return errors
#
#
# def sanity_check_events(driver_path,directory_name, logging_level=logging.INFO):
#     """
#     Checks if thes file within a directoy have been correctly downloaded
#
#     :param directory_name: String
#     :param logging_level: logging object
#     """
#     logging.basicConfig(level=logging_level)
#     logger = logging.getLogger(__name__)
#
#     driver = create_driver(driver_path)
#
#     errors = []
#     directory = os.fsencode(directory_name)
#     for file in [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]:
#         with open(os.path.join(directory, file), encoding="utf-8") as f:
#             raw_html = f.read()
#
#             doc = pq(raw_html)
#             if doc("title").text() == '404 Not Found':
#                 errors.append(os.fsdecode(file))
#
#             filename=file.decode("utf-8")
#             statinfo=os.stat(directory_name+filename)
#
#             #we assume that the event files with a size lower than 100kB need to be revised and download again.
#             if statinfo.st_size <100000:
#                 logger.info(filename+' was not properly downladed. Missing data.')
#                 game_event_id = os.path.splitext(filename)[0]
#                 event_id=game_event_id.split("-")[1]
#                 eventURL = "http://www.fibalivestats.com/u/ACBS/{}/pbp.html".format(event_id)
#                 driver.get(eventURL)
#                 html = driver.page_source
#                 time.sleep(1)
#                 save_content(directory_name+filename, html)
#                 errors.append(filename)
#
#             statinfo2=os.stat(directory_name+filename)
#             f.close()
#             if statinfo2.st_size < 250000:
#                 logger.info('The game-event ' + filename +' data is not correct. Missing data. Deleting game-event...')
#                 try:
#                     os.remove(directory_name+filename)
#                     logger.info('game-event ' + filename + ' deleted...')
#                     continue
#
#                 except:
#                     logger.info('game-event ' + filename + ' cannot be deleted...')
#                     continue
#
#     #recursive call to sanity_check to check if there are more errors with the html
#     if errors:
#         logger.info('There were {} errors in the downloads!'.format(len(errors)))
#         sanity_check_events(driver_path,directory_name, logging_level=logging.INFO)
#
#     driver.close()
#     driver.quit()
#     logger.info('Sanity check of {} correctly finished!\n'.format(os.fsdecode(directory)))
#     return errors
#
# def sanity_check_shotchart(driver_path,directory_name, logging_level=logging.INFO):
#     """
#     Checks if thes file within a directoy have been correctly downloaded
#
#     :param directory_name: String
#     :param logging_level: logging object
#     """
#     logging.basicConfig(level=logging_level)
#     logger = logging.getLogger(__name__)
#
#     driver = create_driver(driver_path)
#
#     errors = []
#     directory = os.fsencode(directory_name)
#     for file in [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]:
#         with open(os.path.join(directory, file), encoding="utf-8") as f:
#             raw_html = f.read()
#
#             doc = pq(raw_html)
#             if doc("title").text() == '404 Not Found':
#                 errors.append(os.fsdecode(file))
#
#             filename=file.decode("utf-8")
#             statinfo=os.stat(directory_name+filename)
#
#             #we assume that the shotchart files with a size lower than 69kB need to be revised and download again.
#             if statinfo.st_size <69000:
#                 logger.info(filename+' was not properly downladed. Missing data.')
#                 game_shotchart_id = os.path.splitext(filename)[0]
#                 shotchart_id=game_shotchart_id.split("-")[1]
#                 shotchartURL = "http://www.fibalivestats.com/u/ACBS/{}/sc.html".format(shotchart_id)
#                 driver.get(shotchartURL)
#                 html = driver.page_source
#                 time.sleep(1)
#                 save_content(directory_name+filename, html)
#                 errors.append(filename)
#
#             statinfo2=os.stat(directory_name+filename)
#             f.close()
#             if statinfo2.st_size < 69000:
#                 logger.info('The game-shotchart ' + filename +' data is not correct. Missing data. Deleting game-shotchart...')
#                 try:
#                     os.remove(directory_name+filename)
#                     logger.info('game-shotchart ' + filename + ' deleted...')
#                     continue
#
#                 except:
#                     logger.info('game-shotchart ' + filename + ' cannot be deleted...')
#                     continue
#
#     #recursive call to sanity_check to check if there are more errors with the html
#     if errors:
#         logger.info('There were {} errors in the downloads!'.format(len(errors)))
#         sanity_check_shotchart(driver_path,directory_name, logging_level=logging.INFO)
#
#     driver.close()
#     driver.quit()
#     logger.info('Sanity check of {} correctly finished!\n'.format(os.fsdecode(directory)))
#     return errors
#
# def sanity_check_shotchart_copa(driver_path,directory_name, logging_level=logging.INFO):
#     """
#     Checks if thes file within a directoy have been correctly downloaded
#
#     :param directory_name: String
#     :param logging_level: logging object
#     """
#     logging.basicConfig(level=logging_level)
#     logger = logging.getLogger(__name__)
#
#     driver = create_driver(driver_path)
#
#     errors = []
#     directory = os.fsencode(directory_name)
#     for file in os.listdir(directory):
#         with open(os.path.join(directory, file), encoding="utf-8") as f:
#             raw_html = f.read()
#
#             doc = pq(raw_html)
#             if doc("title").text() == '404 Not Found':
#                 errors.append(os.fsdecode(file))
#
#             filename=file.decode("utf-8")
#             statinfo=os.stat(directory_name+filename)
#
#             #we assume that the shotchart files with a size lower than 69kB need to be revised and download again.
#             if statinfo.st_size <69000:
#                 logger.info(filename+' was not properly downladed. Missing data.')
#                 game_shotchart_id = os.path.splitext(filename)[0]
#                 shotchart_id=game_shotchart_id.split("-")[1]
#                 shotchartURL = "http://www.fibalivestats.com/u/ACBS/{}/sc.html".format(shotchart_id)
#                 driver.get(shotchartURL)
#                 html = driver.page_source
#                 time.sleep(1)
#                 save_content(directory_name+filename, html)
#                 errors.append(filename)
#
#             statinfo2=os.stat(directory_name+filename)
#             f.close()
#             if statinfo2.st_size < 69000:
#                 logger.info('The game-shotchart ' + filename +' data is not correct. Missing data. Deleting game-shotchart...')
#                 try:
#                     os.remove(directory_name+filename)
#                     logger.info('game-shotchart ' + filename + ' deleted...')
#                     continue
#
#                 except:
#                     logger.info('game-shotchart ' + filename + ' cannot be deleted...')
#                     continue
#
#     #recursive call to sanity_check to check if there are more errors with the html
#     if errors:
#         logger.info('There were {} errors in the downloads!'.format(len(errors)))
#         sanity_check_shotchart(driver_path,directory_name, logging_level=logging.INFO)
#
#     driver.close()
#     driver.quit()
#     logger.info('Sanity check of {} correctly finished!\n'.format(os.fsdecode(directory)))
#     return errors