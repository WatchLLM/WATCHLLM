import os

VALID_MODES = {'enforce', 'shadow'}


def load_mode() -> str:
    mode = os.environ.get('WATCHLLM_MODE', 'enforce').strip().lower()

    if mode in VALID_MODES:
        return mode

    raise ValueError('Invalid WATCHLLM_MODE')


def set_mode(mode: str) -> None:
    value = mode.strip().lower()

    if value not in VALID_MODES:
        raise ValueError('Invalid WATCHLLM_MODE')

    os.environ['WATCHLLM_MODE'] = value
