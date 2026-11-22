"""Text chunking for runbook / post-mortem embedding.

Deterministic, boundary-safe character chunking with overlap. Every character
of the input is emitted exactly once across the returned chunks (no data loss
at chunk boundaries), which keeps embedding recall predictable and makes the
chunk count easy to reason about in tests.
"""



def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split *text* into overlapping chunks of at most *chunk_size* characters.

    Consecutive chunks overlap by *overlap* characters so that no term is split
    across a boundary without context. The final chunk may be shorter than
    *chunk_size*.

    Args:
        text: The source text to chunk.
        chunk_size: Maximum number of characters per chunk (must be > 0).
        overlap: Number of characters shared between adjacent chunks
            (must be >= 0 and < chunk_size).

    Returns:
        A list of chunk strings. Empty input yields an empty list.

    Raises:
        ValueError: If *chunk_size* is not positive or *overlap* is out of
            range.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must satisfy 0 <= overlap < chunk_size")
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    total = len(text)

    while start < total:
        end = min(start + chunk_size, total)
        chunks.append(text[start:end])
        if end >= total:
            break
        start = end - overlap

    return chunks


def merge_chunks(chunks: list[str], overlap: int) -> str:
    """Reassemble chunks produced by :func:`chunk_text` by dropping the
    overlapping tail of each chunk except the last.

    This is the inverse of :func:`chunk_text` for the no-data-loss property:
    ``merge_chunks(chunk_text(text, size, overlap), overlap) == text``.
    """
    if not chunks:
        return ""
    result = chunks[0]
    for chunk in chunks[1:]:
        result += chunk[overlap:]
    return result
