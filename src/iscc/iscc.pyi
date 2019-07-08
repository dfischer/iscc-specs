# -*- coding: utf-8 -*-
from typing import *
from PIL import Image
from io import BytesIO

B = TypeVar("B", str, BinaryIO, bytes)
IMG = TypeVar("I", str, BytesIO, Image.Image)
TEXT = TypeVar("TEXT", str, bytes)

# Top Level Functions
def meta_id(
    title: Union[str, bytes], extra: Union[str, bytes] = ""
) -> Tuple[str, str, str]: ...
def content_id_text(text: Union[str, bytes], partial=False) -> str: ...
def content_id_image(img: IMG, partial: bool = False) -> str: ...
def content_id_mixed(cids: List[str], partial: bool = False) -> str: ...
def data_id(data: B) -> str: ...
def instance_id(data: B) -> Tuple[str, str]: ...

# Content Normalization
def text_pre_normalize(text: TEXT) -> str: ...
def text_trim(text: str) -> str: ...
def text_normalize(text: str, keep_ws: bool = False) -> str: ...
def image_normalize(img: IMG) -> List[List[int]]: ...

# Feature Hashing
def similarity_hash(hash_digests: Sequence[ByteString]) -> bytes: ...
def minimum_hash(features: Iterable[int], n: int = 64) -> List[int]: ...
def image_hash(pixels: List[List[int]]) -> bytes: ...

# Content-ID-Image utils
def dct(value_list: Sequence[float]) -> Sequence[float]: ...

# Data-ID utils
def data_chunks(data: B) -> Generator[bytes, None, None]: ...
def chunk_length(
    data: bytes, norm_size: int, min_size: int, max_size: int, mask_1: int, mask_2: int
) -> int: ...

# Instance-ID helpers
def sha256d(data: bytes) -> bytes: ...
def top_hash(hashes: List[bytes]) -> bytes: ...
def hash_inner_nodes(a: bytes, b: bytes) -> bytes: ...

# Common untility functions
def sliding_window(seq: Sequence, width: int) -> List: ...
def distance(a: Union[int, str, bytes], b: Union[int, str, bytes]) -> int: ...
def encode(digest: bytes) -> str: ...
def decode(code: str) -> bytes: ...
