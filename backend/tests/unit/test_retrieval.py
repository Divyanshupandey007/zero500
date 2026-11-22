"""Unit tests for the pgvector retrieval query builder.

These tests assert the SQL and parameters produced by
``VectorStore.search_similar_docs`` for a given query embedding, using a fully
mocked database connection. No real PostgreSQL/pgvector instance is required.
"""

from typing import Any
from unittest.mock import MagicMock

from app.services.vector_store import VectorStore


def _make_vector_store(mocker: Any) -> VectorStore:
    store = VectorStore.__new__(VectorStore)
    # Skip __init__ (it validates env and builds a Gemini client).
    store.gemini_client = MagicMock()
    # Deterministic embedding; no real Gemini call.
    mocker.patch.object(store, "get_embedding", return_value=[0.1, 0.2, 0.3])

    # A single shared connection/cursor so the assertions below inspect the
    # exact call made inside search_similar_docs.
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = False
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False
    mocker.patch.object(store, "get_connection", return_value=conn)
    return store, cursor


def test_search_similar_docs_uses_cosine_distance_and_limit(mocker: Any) -> None:
    store, cursor = _make_vector_store(mocker)

    results = store.search_similar_docs("connection pool exhaustion", limit=3)

    assert results == []
    assert cursor.execute.called, "expected a query to be executed"
    sql, params = cursor.execute.call_args.args

    # Cosine-distance retrieval via the pgvector <=> operator.
    assert "<=>" in sql, f"expected cosine-distance operator in SQL: {sql}"
    assert "ORDER BY embedding <=> %s::vector ASC" in sql, sql
    assert "LIMIT %s" in sql, sql

    # Query vector bound twice (once for score, once for ordering) + limit.
    assert params == ([0.1, 0.2, 0.3], [0.1, 0.2, 0.3], 3), params


def test_search_similar_docs_default_limit_is_two(mocker: Any) -> None:
    store, cursor = _make_vector_store(mocker)

    store.search_similar_docs("any query")

    _, params = cursor.execute.call_args.args
    assert params[2] == 2, f"expected default limit 2, got {params}"


def test_search_similar_docs_embedding_is_mocked(mocker: Any) -> None:
    """Confirm get_embedding is invoked with the query text (no real Gemini)."""
    store, _cursor = _make_vector_store(mocker)
    store.search_similar_docs("kernel panic on node-7")
    store.get_embedding.assert_called_once_with("kernel panic on node-7")


def test_search_similar_docs_maps_rows_to_results(mocker: Any) -> None:
    store, cursor = _make_vector_store(mocker)
    # Simulate one row returned by pgvector.
    cursor.fetchall.return_value = [
        (1, "Runbook: X", "svc", "RUNBOOK", "content here", 0.91)
    ]

    results = store.search_similar_docs("query")

    assert len(results) == 1
    row = results[0]
    assert row["id"] == 1
    assert row["title"] == "Runbook: X"
    assert row["doc_type"] == "RUNBOOK"
    assert row["content"] == "content here"
    assert row["similarity_score"] == 0.91

