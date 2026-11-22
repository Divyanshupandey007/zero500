"""Unit tests for the runbook/post-mortem chunking function.

Covers chunk sizes, overlap, boundary behaviour and the no-data-loss round-trip
property.
"""

import pytest

from app.data.chunking import chunk_text, merge_chunks


def test_chunk_sizes_do_not_exceed_chunk_size() -> None:
    text = "x" * 1000
    chunks = chunk_text(text, chunk_size=300, overlap=50)
    assert all(len(chunk) <= 300 for chunk in chunks)


def test_consecutive_chunks_overlap_by_configured_amount() -> None:
    text = "a" * 1000
    overlap = 50
    chunks = chunk_text(text, chunk_size=300, overlap=overlap)
    for first, second in zip(chunks, chunks[1:]):
        assert first[-overlap:] == second[:overlap]


def test_single_chunk_when_text_shorter_than_chunk_size() -> None:
    chunks = chunk_text("hello world", chunk_size=1000, overlap=100)
    assert chunks == ["hello world"]


def test_empty_text_yields_no_chunks() -> None:
    assert chunk_text("", chunk_size=300, overlap=50) == []


def test_chunk_boundaries_advance_by_chunk_size_minus_overlap() -> None:
    text = "".join(chr(ord("a") + i % 26) for i in range(1000))
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    starts = []
    cursor = 0
    for chunk in chunks:
        starts.append(cursor)
        cursor += len(chunk) - 20
    # Each start after the first advances by chunk_size - overlap (80).
    assert all(b - a == 80 for a, b in zip(starts, starts[1:]))

def test_no_data_loss_at_chunk_boundaries_round_trip() -> None:
    text = (
        "The quick brown fox jumps over the lazy dog. " * 40
    )  # ~1000 characters
    for chunk_size, overlap in [(100, 10), (500, 50), (250, 0), (63, 17)]:
        chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        assert merge_chunks(chunks, overlap) == text, (
            f"data loss for chunk_size={chunk_size}, overlap={overlap}"
        )


def test_invalid_chunk_size_raises() -> None:
    with pytest.raises(ValueError):
        chunk_text("abc", chunk_size=0, overlap=0)
    with pytest.raises(ValueError):
        chunk_text("abc", chunk_size=-5, overlap=0)


def test_invalid_overlap_raises() -> None:
    with pytest.raises(ValueError):
        chunk_text("abc", chunk_size=10, overlap=10)
    with pytest.raises(ValueError):
        chunk_text("abc", chunk_size=10, overlap=-1)
