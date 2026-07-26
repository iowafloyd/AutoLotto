import os
import sys
import time

ERROR_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'error.log')


def log_error(message):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    full_message = f'[{timestamp}] {message}'
    print(f'ERROR: {full_message}', file=sys.stderr)
    with open(ERROR_LOG_PATH, 'a', encoding='utf-8') as handle:
        handle.write(full_message + '\n')


def log_completion(reason):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    message = f'Program completed at {timestamp} ({reason}) \n'
    print(message)
    with open(ERROR_LOG_PATH, 'a', encoding='utf-8') as handle:
        handle.write(f'[{timestamp}] {message}\n')
