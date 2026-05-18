from pathlib import Path
import os


TOKEN_PATH = Path(os.environ.get('WATCHLLM_TOKEN_PATH', str(Path.home() / '.watchllm' / 'token')))


def save_token(token: str) -> None:
    value = token.strip()

    if not value:
        raise ValueError('Token is required')

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(value, encoding='utf-8')


def load_token() -> str:
    if not TOKEN_PATH.exists():
        raise FileNotFoundError('Token not found')

    token = TOKEN_PATH.read_text(encoding='utf-8').strip()

    if not token:
        raise ValueError('Token is empty')

    return token
