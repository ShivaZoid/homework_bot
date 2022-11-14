from http import HTTPStatus
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import time

from dotenv import load_dotenv
import requests
import telegram


load_dotenv()

PRACTICUM_TOKEN = os.getenv('YANDEX_TOKEN')
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('MY_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, [%(levelname)s], %(message)s',
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'my_logger.log',
    encoding='UTF-8',
    maxBytes=50000000,
    backupCount=5,
)
logger.addHandler(handler)

formatter = logging.Formatter(
    '%(asctime)s, [%(levelname)s], %(message)s'
)
handler.setFormatter(formatter)


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


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logger.info(
            'Отправлено сообщение в чат {TELEGRAM_CHAT_ID}: {message}'
        )
    except telegram.TelegramError as telegram_error:
        logger.error(f'Ошибка отправки сообщения {telegram_error}')


def get_api_answer(current_timestamp):
    """Делает запрос к API-сервису."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        homework_response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params,
        )
    except requests.exceptions.RequestException as requests_error:
        api_answer_error = f'Ошибка при запросе к API: {requests_error}'
        logger.error(api_answer_error)
        raise RequestExceptionError(api_answer_error) from requests_error

    status_code = homework_response.status_code
    if status_code != HTTPStatus.OK:
        status_code_error = f'Ошибка {status_code}'
        logger.error(status_code_error)
        raise StatusCodeError(status_code_error)

    try:
        return homework_response.json()
    except json.JSONDecodeError as json_error:
        api_answer_error = f'Ошибка ответа формата json {json_error}'
        logger.error(api_answer_error)
        raise json.JSONDecodeError(api_answer_error) from json_error


def check_response(response):
    """Проверяет ответ API на корректность."""
    if response is None:
        response_error = 'response имеет неправильное значение'
        logger.error(response_error)
        raise DictionaryError(response_error)

    if type(response) is not dict:
        logger.error('Ответ не является словарем')
        raise TypeError('Ответ не является словарем')

    if type(response['homeworks']) is not list:
        logger.error('Домашняя работа не является списком')
        raise TypeError('Домашняя работа не является списком')

    if not response['homeworks']:
        logger.info('Список домашних работ пуст')
        raise KeyError('Список домашних работ пуст')

    return response['homeworks']


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе.

    статус этой работы.
    """
    homework_name = homework['homework_name']
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')

    homework_status = homework['status']
    if 'status' not in homework:
        raise KeyError('Отсутствует ключ "status" в ответе API')

    if homework_status not in HOMEWORK_STATUSES:
        error = f'Неизвестный статус работы: {homework_status}'
        raise UnknownStatusError(error)

    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_os_keys():
    """Проверка токенов в системе."""
    keys = [
        'YANDEX_TOKEN',
        'BOT_TOKEN',
        'MY_ID',
    ]

    for key in keys:
        if key in os.environ:
            return True


def check_tokens():
    """Проверка доступности переменных окружения."""
    if all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)):
        return True


def main():
    """Основная логика работы бота."""
    if not check_os_keys():
        token_error = 'Отсутствует токен в системе'
        logging.critical(token_error)
        raise TokenSystemError(token_error)

    if not check_tokens():
        variable_error = 'Отсутствует переменная окружения'
        logging.critical(variable_error)
        raise EnvironmentVariableError(variable_error)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status = ''
    message_error = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)[0]
            if homework and status != homework['status']:
                message = parse_status(homework)
                send_message(bot, message)
                status = homework['status']
                logger.info(
                    (f'Есть изменения, <<{status}>>. Повторный запрос к API '
                     'через 10 минут')
                )
                time.sleep(RETRY_TIME)
            else:
                logger.info(
                    ('Изменений нет, повторный запрос к API '
                     'через 10 минут')
                )
                time.sleep(RETRY_TIME)
        except Exception as error:
            logging.error(error)
            message = f'Сбой в работе программы: {error}'
            if message != message_error:
                send_message(bot, message)
            logger.info(
                'Сбой программы, повторный запрос к API через 10 минут'
            )
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
