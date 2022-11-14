class RequestExceptionError(Exception):
    """Ошибка при запросе."""


class StatusCodeError(Exception):
    """Ошибка ответа сервера."""


class DictionaryError(Exception):
    """Ошибка полученного словаря."""


class UnknownStatusError(Exception):
    """Неизвестный статус работы."""


class TokenSystemError(Exception):
    """Отсутствует токен в системе."""


class EnvironmentVariableError(Exception):
    """Отсутствует переменная окружения."""
