# -*- coding: utf-8 -*-
import iscc
import iscc_samples


def test_code_content_handles_mediatypes():
    result = iscc.code_content(iscc_samples.texts()[0])
    assert isinstance(result, dict)
