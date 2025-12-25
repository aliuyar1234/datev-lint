"""Lightweight fuzz tests for the CSV tokenizer.

These tests are deterministic (seeded) and focus on robustness: the tokenizer
must not crash or produce invalid line spans for arbitrary input.
"""

from __future__ import annotations

import random
import string

from datev_lint.core.parser.models import Dialect
from datev_lint.core.parser.tokenizer import tokenize_stream


def _random_text(rng: random.Random, max_len: int = 5000) -> str:
    alphabet = string.ascii_letters + string.digits + " ;,.-_()[]{}" + '"' + "\r" + "\n"
    length = rng.randint(0, max_len)
    return "".join(rng.choice(alphabet) for _ in range(length))


def test_tokenize_stream_fuzz_does_not_crash() -> None:
    rng = random.Random(1337)  # noqa: S311
    dialect = Dialect()

    for _ in range(250):
        text = _random_text(rng)
        last_end = 0

        for fields, start_line, end_line in tokenize_stream(text, dialect):
            assert isinstance(fields, list)
            assert start_line >= 1
            assert end_line >= start_line
            assert end_line >= last_end
            last_end = end_line
