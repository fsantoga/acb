import os
import logging

from datetime import datetime
from utils import LoggerException

logger = logging.getLogger(__name__)


def init_logging(file_name, log_path=None, level=logging.INFO):
    """
    Init the logging system.
    :param file_name: The prefix file name.
    :param log_path: Log path if any
    :param level: logging level
    :return: None.
    """
    global logger

    try:
        if not log_path:
            log_path = '../logs'
    except KeyError as e:
        raise LoggerException(message=str(e))

    log_path = os.path.join(log_path, file_name + "-" + datetime.utcnow().strftime("%Y%m%d-%H%M%S") + '.log')

    logging.basicConfig(
        filename=log_path,
        format='%(asctime)s - %(levelname)s: %(message)s',
        level=level,
    )
