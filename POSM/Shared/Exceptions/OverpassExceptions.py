from requests import RequestException


class OverpassRequestException(RequestException):
    pass


class UnknownException(OverpassRequestException):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class RequestSyntaxException(OverpassRequestException):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class TooManyRequestsException(OverpassRequestException):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class TimeoutException(OverpassRequestException):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class OsmnxException(RuntimeError):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)