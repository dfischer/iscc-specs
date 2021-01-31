# -*- coding: utf-8 -*-
from loguru import logger
import json
import iscc


REQUIRED = (
    "meta_id",
    "content_id_text",
    "content_id_image",
    "content_id_mixed",
    "data_id",
    "instance_id",
)


def main():
    data = json.load(open("test_inputs.json", "r", encoding="utf-8"))

    for funcname, tests in data.items():
        for testname, testdata in tests.items():
            func = getattr(iscc, funcname)
            args = testdata["inputs"]
            logger.debug(func)
            result = func(*args)
            if funcname in ["data_chunks"]:
                result = ["hex:" + data.hex() for data in result]
            testdata["outputs"] = result
        data[funcname]["required"] = funcname in REQUIRED
    with open("test_data.json", "w", encoding="utf-8") as outf:
        json.dump(data, outf, indent=2, sort_keys=True, ensure_ascii=False)


if __name__ == "__main__":
    main()
