from httpx import RequestError


class DataFetchError(RequestError):
    """something error when fetch"""


class IPBlockError(RequestError):
    """fetch so fast that the server block us ip"""


class Over10Exception(ValueError):
    """fetch so fast that the server block us ip"""


class PasswordException(ValueError):
    """密码错误"""
    pass


class FaceCollectionException(ValueError):
    pass

class VerifyException(ValueError):
    pass

