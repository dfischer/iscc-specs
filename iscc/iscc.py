# -*- coding: utf-8 -*-
"""ISCC Reference Implementation"""
from statistics import median
import math
from io import BytesIO
from hashlib import sha256
import unicodedata
from typing import List, ByteString, Sequence, BinaryIO, TypeVar, Generator, Union, Iterable, Tuple
from PIL import Image
from copy import deepcopy
import xxhash
from . import const

B = TypeVar('B', BinaryIO, bytes)
IMG = TypeVar('I', str, BytesIO, Image.Image)


def meta_id(title: Union[str, bytes], extra: Union[str, bytes]='', version: int=0) -> Tuple[str, str, str]:

    assert version == 0, "Only version 0 supported"

    # 1. Apply Unicode NFKC normalization separately to all text input values.
    if isinstance(title, bytes):
        title = title.decode('utf-8')
    title = unicodedata.normalize('NFKC', title)

    if isinstance(extra, bytes):
        extra = extra.decode('utf-8')
    extra = unicodedata.normalize('NFKC', extra)

    # 2. Trim title and extra
    title = trim(title)
    extra = trim(extra)

    # 3. Concatenate
    concat = '\u0020'.join((title, extra)).strip()

    # 4. Apply text normalization
    normalized = normalize_text(concat)

    # 5. Create a list of n-grams
    n_grams = sliding_window(normalized, width=const.WINDOW_SIZE_MID)

    # 6. Encode n-grams and create xxhash64-digest
    hash_digests = [xxhash.xxh64(s.encode('utf-8')).digest() for s in n_grams]

    # 7. Apply similarity_hash
    simhash_digest = similarity_hash(hash_digests)

    # 8. Prepend header-byte
    meta_id_digest = const.HEAD_MID + simhash_digest

    # 9. Encode with base58_iscc
    return encode(meta_id_digest), title, extra


def content_id_text(text: Union[str, bytes], partial=False) -> str:

    # 1. Apply Unicode NFKC normalization
    if isinstance(text, bytes):
        text = text.decode('utf-8')
    text = unicodedata.normalize('NFKC', text)

    # 2. Apply `normalize_text`
    text = normalize_text(text)

    # 3. Split to words
    words = text.split()

    # 4. Create 5 word shingles
    shingles = ('\u0020'.join(l) for l in sliding_window(words, const.WINDOW_SIZE_CID_T))

    # 5. Create 32-bit features with xxHash32
    features = (xxhash.xxh32(s.encode('utf-8')).intdigest() for s in shingles)

    # 6. Apply minimum_hash
    minhash = minimum_hash(features)

    # 7. Collect least significant bits
    lsb = ''.join([str(x & 1) for x in minhash])

    # 8. Create two 64-bit digests
    a = int(lsb[:64], 2).to_bytes(8, 'big', signed=False)
    b = int(lsb[64:], 2).to_bytes(8, 'big', signed=False)

    # 9. Apply simhash to digests
    simhash_digest = similarity_hash((a, b))

    # 10. Prepend component header
    if partial:
        content_id_text_digest = const.HEAD_CID_T_PCF + simhash_digest
    else:
        content_id_text_digest = const.HEAD_CID_T + simhash_digest

    # 11. Encode and return
    return encode(content_id_text_digest)


def content_id_image(img: IMG, partial=False) -> str:

    if not isinstance(img, Image.Image):
        img = Image.open(img)

    # 1. Convert to greyscale
    img = img.convert("L")

    # 2. Resize to 64x64
    img = img.resize((32, 32), Image.BICUBIC)

    # 3. Create two dimensional array
    pixels = [[list(img.getdata())[32 * i + j] for j in range(32)] for i in range(32)]

    # 4. DCT per row & col
    dct_row_lists = []
    for pixel_list in pixels:
        dct_row_lists.append(dct(pixel_list))

    dct_row_lists_t = list(map(list, zip(*dct_row_lists)))
    dct_col_lists_t = []
    for dct_list in dct_row_lists_t:
        dct_col_lists_t.append(dct(dct_list))

    dct_lists = list(map(list, zip(*dct_col_lists_t)))

    # 5. Extract upper left 8x8 corner
    flat_list = [x for sublist in dct_lists[:8] for x in sublist[:8]]

    # 6. Calculate median
    med = median(flat_list)

    # 7. Create 64-bit digest by comparing to median
    bitstring = ''
    for value in flat_list:
        if value > med:
            bitstring += '1'
        else:
            bitstring += '0'
    hash_digest = int(bitstring, 2).to_bytes(8, 'big', signed=False)

    # 8. Prepend the 1-byte component header
    if partial:
        content_id_image_digest = const.HEAD_CID_I_PCF + hash_digest
    else:
        content_id_image_digest = const.HEAD_CID_I + hash_digest

    # 9. Encode and return
    return encode(content_id_image_digest)


def data_id(data: B) -> str:

    # 1. & 2. XxHash32 over CDC-Chunks
    features = (xxhash.xxh32(chunk).intdigest() for chunk in data_chunks(data))

    # 3. Apply minimum_hash
    minhash = minimum_hash(features)

    # 4. Collect least significant bits
    lsb = ''.join([str(x & 1) for x in minhash])

    # 5. Create two 64-bit digests
    a = int(lsb[:64], 2).to_bytes(8, 'big', signed=False)
    b = int(lsb[64:], 2).to_bytes(8, 'big', signed=False)

    # 6. Apply simhash
    simhash_digest = similarity_hash((a, b))

    # 7. Prepend the 1-byte header
    data_id_digest = const.HEAD_DID + simhash_digest

    # 8. Encode and return
    return encode(data_id_digest)


def instance_id(data: B) -> str:

    if not hasattr(data, 'read'):
        data = BytesIO(data)

    leaf_node_digests = []

    while True:
        chunk = data.read(64000)
        if chunk:
            leaf_node_digests.append(sha256d(b'\x00' + chunk))
        else:
            break

    top_hash_digest = top_hash(leaf_node_digests)
    instance_id_digest = const.HEAD_IID + top_hash_digest[:8]

    return encode(instance_id_digest)


def trim(text: str) -> str:
    """Trim text so utf-8 encoded bytes do not exceed INPUT_TRIM size."""
    while True:
        data = text.encode('utf-8')
        if len(data) <= const.INPUT_TRIM:
            return text
        else:
            text = text[:-1]


def top_hash(hashes: List[bytes]) -> bytes:

    size = len(hashes)
    if size == 1:
        return hashes[0]

    pairwise_hashed = []

    for i in range(0, len(hashes) - 1, 2):
        pairwise_hashed.append(hash_inner_nodes(hashes[i], hashes[i + 1]))

    if size % 2 == 1:
        pairwise_hashed.append(hash_inner_nodes(hashes[-1], hashes[-1]))

    return top_hash(pairwise_hashed)


def sha256d(data: bytes) -> bytes:
    return sha256(sha256(data).digest()).digest()


def hash_inner_nodes(a: bytes, b: bytes) -> bytes:
    return sha256d(b'\x01' + a + b)


def data_chunks(data: B) -> Generator[bytes, None, None]:

    if not hasattr(data, 'read'):
        data = BytesIO(data)

    section = data.read(640)
    counter = 0
    while True:
        if counter < 100:
            if len(section) < 640:
                section += data.read(640)
            if len(section) == 0:
                break
            boundary = chunk_length(section, 40, 20, 640, 0x016118, 0x00a0b1)
        else:
            if len(section) < 65536:
                section += data.read(65536)
            if len(section) == 0:
                break
            boundary = chunk_length(section, 4096, 2048, 65536, 0x0003590703530000, 0x0000d90003530000)

        yield section[:boundary]
        section = section[boundary:]
        counter += 1


def chunk_length(data: bytes, norm_size: int, min_size: int, max_size: int, mask_1: int, mask_2: int) -> int:
    data_length = len(data)
    i = min_size
    pattern = 0

    if data_length <= min_size:
        return data_length

    while i < min(norm_size, data_length):
        pattern = (pattern << 1) + const.CHUNKING_GEAR[data[i]]
        if not pattern & mask_1:
            return i
        i = i + 1
    while i < min(max_size, data_length):
        pattern = (pattern << 1) + const.CHUNKING_GEAR[data[i]]
        if not pattern & mask_2:
            return i
        i = i + 1
    return i


def normalize_text(text: str) -> str:

    whitelist = 'LNS'
    decomposed = unicodedata.normalize('NFD', text)
    chars = []

    for c in decomposed:
        cat = unicodedata.category(c)
        if cat.startswith('Z'):
            chars.append(' ')
        elif cat[0] in whitelist:
            chars.append(c.lower())

    filtered = ''.join(chars)
    collapsed = '\u0020'.join(filtered.split())
    normalized = unicodedata.normalize('NFC', collapsed)

    return normalized


def sliding_window(text: Sequence, width: int) -> List:
    assert width >= 2, "Sliding window width must be 2 or bigger."
    idx = range(max(len(text) - width + 1, 1))
    return [text[i:i + width] for i in idx]


def minimum_hash(features: Iterable[int]) -> List[int]:

    max_int64 = (1 << 64) - 1
    mersenne_prime = (1 << 61) - 1
    max_hash = (1 << 32) - 1
    hashvalues = [max_hash] * 128
    permutations = deepcopy(const.MINHASH_PERMUTATIONS)
    a, b = permutations

    for hv in features:
        nhs = []
        for x in range(128):
            nh = (((a[x] * hv + b[x]) & max_int64) % mersenne_prime) & max_hash
            nhs.append(min(nh, hashvalues[x]))
        hashvalues = nhs

    return hashvalues


def similarity_hash(hash_digests: Sequence[ByteString]) -> bytes:

    n_bytes = len(hash_digests[0])
    n_bits = (n_bytes * 8)
    vector = [0] * n_bits

    for digest in hash_digests:

        assert len(digest) == n_bytes
        h = int.from_bytes(digest, 'big', signed=False)

        for i in range(n_bits):
            vector[i] += h & 1
            h >>= 1

    minfeatures = len(hash_digests) * 1. / 2
    shash = 0

    for i in range(n_bits):
        shash |= int(vector[i] >= minfeatures) << i

    return shash.to_bytes(n_bytes, 'big', signed=False)


def dct(value_list: Sequence[float]) -> Sequence[float]:
    N = len(value_list)
    dct_list = []
    for k in range(N):
        value = 0.0
        for n in range(N):
            value += value_list[n] * math.cos(math.pi * k * (2 * n + 1) / (2 * N))
        dct_list.append(2 * value)
    return dct_list


def distance(a: Union[int, str, bytes], b: Union[int, str, bytes]) -> int:

    if isinstance(a, str) and isinstance(b, str):
        a = decode(a)[1:]
        b = decode(b)[1:]

    if isinstance(a, bytes) and isinstance(b, bytes):
        a = int.from_bytes(a, 'big', signed=False)
        b = int.from_bytes(b, 'big', signed=False)

    return bin(a ^ b).count('1')


def encode(digest: bytes) -> str:
    if len(digest) == 9:
        return encode(digest[:1]) + encode(digest[1:])
    assert len(digest) in (1, 8), "Digest must be 1, 8 or 9 bytes long"
    digest = reversed(digest)
    value = 0
    numvalues = 1
    for octet in digest:
        octet *= numvalues
        value += octet
        numvalues *= 256
    chars = []
    while numvalues > 0:
        chars.append(value % 58)
        value //= 58
        numvalues //= 58
    return str.translate(''.join([chr(c) for c in reversed(chars)]), const.V2CTABLE)


def decode(code: str) -> bytes:
    n = len(code)
    if n == 13:
        return decode(code[:2]) + decode(code[2:])
    if n == 2:
        bit_length = 8
    elif n == 11:
        bit_length = 64
    else:
        raise ValueError('Code must be 2, 11 or 13 chars. Not %s' % n)
    code = reversed(str.translate(code, const.C2VTABLE))
    value = 0
    numvalues = 1
    for c in code:
        c = ord(c)
        c *= numvalues
        value += c
        numvalues *= 58
    numvalues = 2 ** bit_length
    data = []
    while numvalues > 1:
        data.append(value % 256)
        value //= 256
        numvalues //= 256
    return bytes(reversed(data))
