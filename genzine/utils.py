import io
import re
import string
from contextlib import contextmanager
from pathlib import Path

import boto3

ROOT = Path(__file__).parents[1]
GENZINE = ROOT / 'genzine'
HTML = ROOT / 'html'


def to_camelcase(text: str) -> str:
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = re.sub(' ', '_', text).lower()
    return text


def h1(text: str) -> str:
    return '# ' + text


def h2(text: str) -> str:
    return '## ' + text


def get_s3_path(edition: str | int, fpath: Path) -> Path:
    return Path('assets/images/editions' / str(edition)) / fpath


@contextmanager
def write_image_to_s3(path: Path, mode: str = 'bytes'):
    """Context manager to enable reading/writing into the S3 bucket.

    Examples:

        >>> image_raw = requests.get(image_url).content
        >>> remote_path = get_s3_path(edition=1, fpath=Path("article_pic.png"))
        >>> with s3.write_image_to_s3(
        ...     path=remote_path,
        ...     mode="bytes"
        ... ) as f:
        ...     f.write(image_raw)

    """
    bucket = boto3.resource('s3').Bucket('gen-zine.co.uk')

    if path.suffix.lower() not in ('jpeg', 'jpg', 'png'):
        raise ValueError('fname must include image suffix')

    obj = bucket.Object(path)

    if mode == 'bytes':
        buffer = io.BytesIO()
    elif mode == 'string':
        buffer = io.StringIO()
    else:
        raise ValueError(f"mode must be 'string' or 'bytes' not {mode}")

    try:
        yield buffer
    finally:
        obj.put(Body=buffer.getvalue())


if __name__ == '__main__':
    pass
