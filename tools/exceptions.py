class LoggerException(Exception):
    def __init__(self, message):
        """Exception class for Logger.

            :param message: Description
            :type message: str
        """
        super().__init__(message)


class InvalidCallException(Exception):
    def __init__(self, message=''):
        """Exception class for Logger.

            :param message: Description
            :type message: str
        """
        super().__init__(message)


class DuplicatedActorId(Exception):
    def __init__(self, message=''):
        """Exception class for Logger.

            :param message: Description
            :type message: str
        """
        super().__init__(message)