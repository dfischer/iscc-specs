# -*- coding: utf-8 -*-
import pytest
from iscc.core import content_id_text
from iscc.text import *
from iscc.metrics import distance, distance_hex
from fauxfactory.factories.strings import gen_utf8


TEXT_A = u"""
    Their most significant and usefull property of similarity-preserving
    fingerprints gets lost in the fragmentation of individual, propietary and
    use case specific implementations. The real benefit lies in similarity
    preservation beyond your local data archive on a global scale accross
    vendors.
"""

TEXT_B = u"""
    The most significant and usefull property of similarity-preserving
    fingerprints gets lost in the fragmentation of individual, propietary and
    use case specific implementations. The real benefit lies in similarity
    preservation beyond your local data archive on a global scale accross
    vendors.
"""

TEXT_C = u"""
    A need for open standard fingerprinting. We don´t need the best
    Fingerprinting algorithm just an accessible and widely used one.
"""


def test_content_id_text():
    cid_t_np = content_id_text("")
    assert len(cid_t_np) == 16
    assert cid_t_np == "EAASL4F2WZY7KBXB"
    cid_t_p = content_id_text("", bits=128)
    assert cid_t_p == "EABSL4F2WZY7KBXBYUZPREWZ26IXU"

    with pytest.raises(AssertionError):
        distance(cid_t_p, cid_t_np)

    cid_t_a = content_id_text(TEXT_A)
    cid_t_b = content_id_text(TEXT_B)
    assert distance(cid_t_a, cid_t_b) == 2


def test_text_hash():
    a = text_hash(TEXT_A).hex()
    b = text_hash(TEXT_B).hex()
    c = text_hash(TEXT_C).hex()
    assert a == "1f869a735c10bf9c32107ab4114e13d2bf93614cda99513ee9f989faf3d6983f"
    assert b == "1f869a735c18bfcc32107ab4114e13d2bf9b614cda91513ee9f189faf3d6987f"
    assert c == "366f2f1b08ba65efbbb48acf4b9953d144be674fa0af8802e7a6f1769b19c576"
    assert distance_hex(a, b) == 7


def test_text_features():
    features = text_features(TEXT_A, avg_size=64, ngram_size=13)
    assert sum(x[0] for x in features) == len(TEXT_A)
    assert features == [
        (88, "Ha83PFApXsU"),
        (43, "tJCNM3GDmqo"),
        (52, "ybOgbVaQd6w"),
        (70, "j97uHe9D0AY"),
        (41, "saWu27FmmP4"),
        (20, "fCr9n6iDBWo"),
    ]
    features = text_features(TEXT_B, avg_size=64, ngram_size=13)
    assert sum(x[0] for x in features) == len(TEXT_B)
    assert features == [
        (20, "XOS48cKcoeg"),
        (66, "nYc2flAhXsU"),
        (43, "tJCNM3GDmqo"),
        (52, "ybOgbVaQd6w"),
        (70, "j97uHe9D0AY"),
        (41, "saWu27FmmP4"),
        (20, "fCr9n6iDBWo"),
    ]


def test_text_chunks():
    txt = gen_utf8(1024 * 100)
    chunks = list(text_chunks(txt, avg_size=1024))
    assert "".join(chunks) == txt


def test_trim_text():
    multibyte_2 = "ü" * 128
    trimmed = text_trim(multibyte_2, 128)
    assert 64 == len(trimmed)
    assert 128 == len(trimmed.encode("utf-8"))

    multibyte_3 = "驩" * 128
    trimmed = text_trim(multibyte_3, 128)
    assert 42 == len(trimmed)
    assert 126 == len(trimmed.encode("utf-8"))

    mixed = "Iñtërnâtiônàlizætiøn☃💩" * 6
    trimmed = text_trim(mixed, 128)
    assert 85 == len(trimmed)
    assert 128 == len(trimmed.encode("utf-8"))


def test_text_normalize():
    txt = "  Iñtërnâtiôn\nàlizætiøn☃💩 –  is a tric\t ky \u00A0 thing!\r"

    normalized = text_normalize(txt)
    assert normalized == "internation alizætiøn☃💩 is a tric ky thing!"

    assert text_normalize(" ") == ""
    assert text_normalize("  Hello  World ? ") == "hello world ?"
    assert text_normalize("Hello\nWorld") == "hello world"
