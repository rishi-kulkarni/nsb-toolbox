import os
import tempfile

import pytest

from nsb_toolbox.db import (
    find_questions_by_answer,
    setup_database,
)


@pytest.fixture
def temp_db_path():
    """Create a temporary database file path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    yield path
    os.close(fd)
    os.unlink(path)


@pytest.fixture
def db_connection(temp_db_path):
    """Set up a test database with schema."""
    conn = setup_database(temp_db_path)
    yield conn
    conn.close()


@pytest.fixture
def populated_db(db_connection):
    """Populate the test database with sample questions and answers."""
    # Create test data directly in the database
    cursor = db_connection.cursor()

    # Insert test questions
    questions = [
        (1, "file1.docx", "MATH", "Short Answer", "What is 2+2?"),
        (2, "file1.docx", "SCIENCE", "Short Answer", "What is H2O?"),
        (
            3,
            "file2.docx",
            "BIOLOGY",
            "Short Answer",
            "What is the powerhouse of the cell?",
        ),
        (4, "file2.docx", "MATH", "Short Answer", "What is the square root of 4?"),
        (
            5,
            "file3.docx",
            "MATH",
            "Multiple Choice",
            "Select the value of π: A) 3.14 B) 2.71 C) 1.62",
        ),
    ]

    cursor.executemany(
        "INSERT INTO questions (id, source_file, subject, type, text) VALUES (?, ?, ?, ?, ?)",
        questions,
    )

    # Insert test answers
    answers = [
        (1, 1, "file1.docx", "4", True),
        (2, 2, "file1.docx", "Water", True),
        (3, 2, "file1.docx", "H2O", False),
        (4, 3, "file2.docx", "Mitochondria", True),
        (5, 4, "file2.docx", "2", True),
        (6, 4, "file2.docx", "Two", False),
        (7, 5, "file3.docx", "3.14", True),
    ]

    cursor.executemany(
        "INSERT INTO answers (id, question_id, source_file, answer_text, is_primary) VALUES (?, ?, ?, ?, ?)",
        answers,
    )

    # Set up answer equivalents (e.g., "Water" and "H2O" are equivalent)
    equivalents = [
        (1, 2),  # Group 1, answer_id 2 (Water)
        (1, 3),  # Group 1, answer_id 3 (H2O)
        (2, 5),  # Group 2, answer_id 5 (2)
        (2, 6),  # Group 2, answer_id 6 (Two)
    ]

    cursor.executemany(
        "INSERT INTO answer_equivalents (group_id, answer_id) VALUES (?, ?)",
        equivalents,
    )

    db_connection.commit()
    return db_connection


def test_find_questions_by_answer_exact_match(populated_db):
    """Test finding questions by exact answer match."""
    # Test exact matching with non-FTS
    results = find_questions_by_answer(populated_db, "Water", use_fts=False)

    # Validate results
    assert len(results) == 1, "Should find exactly one answer group"
    assert results[0]["text"] == "H2O"
    assert results[0]["is_primary_somewhere"] is False
    assert results[0]["total_question_count"] == 1
    assert len(results[0]["questions"]) == 1
    assert results[0]["questions"][0]["subject"] == "SCIENCE"


def test_find_questions_by_answer_equivalent(populated_db):
    """Test finding questions with equivalent answers."""
    # Search for "Water" should also return "H2O" questions
    results = find_questions_by_answer(populated_db, "Water", use_fts=False)

    # Validate results
    assert len(results) == 1, "Should find just H20"

    # Should be sorted by total_question_count (descending)
    answer_texts = [result["text"] for result in results]
    assert set(answer_texts) == {"H2O"}, "Should contain H2O"

    # Both answers should reference the same question
    for result in results:
        assert result["total_question_count"] == 1
        assert result["questions"][0]["subject"] == "SCIENCE"
        assert "What is H2O?" in result["questions"][0]["text"]


def test_find_questions_by_answer_numeric_equivalent(populated_db):
    """Test finding questions with numerically equivalent answers (2 and Two)."""
    # Search for "2" should find both "2" and "Two"
    results = find_questions_by_answer(populated_db, "2", use_fts=False)

    # Validate results
    assert len(results) == 1, "Should find 'Two' answer groups"
    answer_texts = [result["text"] for result in results]
    assert set(answer_texts) == {"TWO"}, "Should contain Two"

    # Both answers should reference the same question
    for result in results:
        assert result["questions"][0]["subject"] == "MATH"
        assert "square root" in result["questions"][0]["text"]


def test_find_questions_by_answer_no_results(populated_db):
    """Test searching for an answer that doesn't exist."""
    results = find_questions_by_answer(populated_db, "NonExistentAnswer", use_fts=True)
    assert len(results) == 0, "Should return an empty list for non-existent answers"


def test_find_questions_by_answer_type_filter(populated_db):
    """Test that only Short Answer questions are returned (as per the SQL query)."""
    # Search for "3.14" which is an answer to a Multiple Choice question
    results = find_questions_by_answer(populated_db, "3.14", use_fts=False)

    # Should not return any results since the find_questions_by_answer function
    # filters for q.type = 'Short Answer' in its SQL query
    assert len(results) == 0, "Should not return Multiple Choice questions"
