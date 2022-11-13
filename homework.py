import logging
import os
import time

import requests
import telegram

from dotenv import load_dotenv
from http import HTTPStatus
from logging.handlers import RotatingFileHandler


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
    except Exception:
        logger.error('Ошибка отправки сообщения')


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
    except Exception as error:
        logging.error(f'Ошибка при запросе к API: {error}')
        raise Exception(f'Ошибка при запросе к API: {error}')

    status_code = homework_response.status_code
    if status_code != HTTPStatus.OK:
        logging.error(f'Ошибка {status_code}')
        raise Exception(f'Ошибка {status_code}')

    try:
        return homework_response.json()
    except ValueError:
        logger.error('Ошибка ответа формата json')
        raise ValueError('Ошибка ответа формата json')


def check_response(response):
    """Проверяет ответ API на корректность."""
    if response is None:
        logger.error('response имеет неправильное значение')
        raise Exception('response имеет неправильное значение')

    if type(response) != dict:
        logger.error('Ответ не является словарем')
        raise TypeError('Ответ не является словарем')

    if type(response['homeworks']) != list:
        logger.error('Домашняя работа не является списком')
        raise TypeError('Домашняя работа не является списком')

    return response['homeworks']


def parse_status(homework):
    """
    Извлекает из информации о конкретной домашней работе статус этой работы.
    """
    homework_name = homework['homework_name']
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')

    homework_status = homework['status']
    if 'status' not in homework:
        raise Exception('Отсутствует ключ "status" в ответе API')

    if homework_status not in HOMEWORK_STATUSES:
        raise Exception(f'Неизвестный статус работы: {homework_status}')

    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_os_keys():
    """Проверка токенов в системе"""
    keys = [
        'YANDEX_TOKEN',
        'BOT_TOKEN',
        'MY_ID',
    ]

    for key in keys:
        if key not in os.environ:
            print(f'Ошибка {key} не назначен.')
            return False
        else:
            return True


def check_tokens():
    """Проверка доступности переменных окружения"""
    if all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)):
        return True
    else:
        return False


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status = ''
    message_error = ''
    if check_os_keys():
        if check_tokens():
            while True:
                try:
                    response = get_api_answer(current_timestamp)
                    if not response['homeworks']:
                        logger.info(
                            'Список домашних работ пуст'
                        )
                        time.sleep(RETRY_TIME)
                    else:
                        homework = check_response(response)[0]
                        if homework and status != homework['status']:
                            message = parse_status(homework)
                            send_message(bot, message)
                            status = homework['status']
                            logger.info((f'Есть изменения, <<{status}>>'))
                            time.sleep(RETRY_TIME)
                        else:
                            logger.info(
                                ('Изменений нет, повторный запрос к API'
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
        else:
            logging.critical(
                'Отсутствует переменная окружения'
            )
            raise Exception(
                'Отсутствует переменная окружения'
            )
    else:
        logging.critical(
            'Отсутствует токен в системе'
        )
        raise Exception(
            'Отсутствует токен в системе'
        )


if __name__ == '__main__':
    main()
