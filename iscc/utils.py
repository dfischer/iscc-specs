# -*- coding: utf-8 -*-
import requests
from loguru import logger
import hashlib
import io
import os
import re
from pathlib import Path
from typing import BinaryIO, Sequence, Generator, Union
from urllib.parse import urlparse
import iscc


File = Union[str, bytes, BinaryIO, Path]


class Streamable:
    """Converts a file path or raw bytes into a managed readable stream."""

    def __init__(self, data: File, close=True):
        self.do_close = close
        if isinstance(data, (str, Path)):
            self.stream = open(data, "rb")
            self.name = Path(data).name
        elif not hasattr(data, "read"):
            self.stream = io.BytesIO(data)
            self.name = ""
        else:
            self.stream = data
            self.name = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.do_close:
            self.stream.close()


class cd:
    """Context manager for changing the current working directory"""

    def __init__(self, new_path):
        self.new_path = os.path.expanduser(new_path)

    def __enter__(self):
        self.saved_path = os.getcwd()
        os.chdir(self.new_path)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.saved_path)


def sliding_window(seq, width):
    # type: (Sequence, int) -> Generator[Sequence[Sequence]]
    """
    Generate a sequence of equal "width" slices each advancing by one elemnt.
    All types that have a length and can be sliced are supported (list, tuple, str ...).
    The result type matches the type of the input sequence.
    Fragment slices smaller than the width at the end of the sequence are not produced.
    If "witdh" is smaller than the input sequence than one element will be returned that
    is shorter than the requested width.
    """
    assert width >= 2, "Sliding window width must be 2 or bigger."
    idx = range(max(len(seq) - width + 1, 1))
    return (seq[i : i + width] for i in idx)


def download_file(url, md5=None, sanitize=False):
    """Download file to app dir and return path."""
    url_obj = urlparse(url)
    file_name = os.path.basename(url_obj.path)
    if sanitize:
        file_name = safe_filename(file_name)
    out_path = os.path.join(iscc.APP_DIR, file_name)
    if os.path.exists(out_path):
        logger.debug(f"Already downloaded: {file_name}")
        if md5:
            md5_calc = hashlib.md5(open(out_path, "rb").read()).hexdigest()
            assert md5 == md5_calc, f"Integrity error for {out_path}"
            return out_path

    r = requests.get(url, stream=True)
    chunk_size = 1024
    iter_size = 0
    with io.open(out_path, "wb") as fd:
        for chunk in r.iter_content(chunk_size):
            fd.write(chunk)
            iter_size += chunk_size

    if md5:
        md5_calc = hashlib.md5(open(out_path, "rb").read()).hexdigest()
        assert md5 == md5_calc, f"Integrity error for {out_path}"
    return out_path


def safe_filename(s: str, max_len: int = 255) -> str:
    """Sanitize a string making it safe to use as a filename.
    See: https://en.wikipedia.org/wiki/Filename.
    """
    ntfs_chars = [chr(i) for i in range(0, 31)]
    chars = [
        r'"',
        r"\#",
        r"\$",
        r"\%",
        r"'",
        r"\*",
        r"\,",
        r"\.",
        r"\/",
        r"\:",
        r'"',
        r"\;",
        r"\<",
        r"\>",
        r"\?",
        r"\\",
        r"\^",
        r"\|",
        r"\~",
        r"\\\\",
    ]
    pattern = "|".join(ntfs_chars + chars)
    regex = re.compile(pattern, re.UNICODE)
    fname = regex.sub("", s)
    return fname[:max_len].rsplit(" ", 0)[0]
