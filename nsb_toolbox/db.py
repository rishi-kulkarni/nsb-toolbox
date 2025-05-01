from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from colorama import Fore, Style

if TYPE_CHECKING:
    from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Answer:
    text: str
    is_primary: bool


@dataclass()
class Question:
    id: int | None
    subject: str
    type: str
    text: str
    answers: List[Answer]
    source_file: str


def extract_text_from_docx(file_path: Path) -> str:
    """Extract all text from a Word document."""
    import docx

    doc = docx.Document(str(file_path))
    return "\n".join(para.text for para in doc.paragraphs)


def preprocess_text(text: str) -> str:
    """
    Normalize whitespace and formatting in the document text to make parsing more reliable.
    """
    # Replace non-breaking spaces with regular spaces
    text = text.replace("\xa0", " ")

    # Normalize different types of dashes (en dash, em dash) to a standard format
    text = re.sub(r"[–—]", "–", text)  # Normalize to en dash

    # Normalize newlines (replace multiple newlines with two newlines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove underscores used as separators
    text = re.sub(r"\n_+\n", "\n\n", text)

    # Ensure consistent spacing around dashes in subject-type format
    text = re.sub(r"(\w+)\s*–\s*(\w+)", r"\1 – \2", text)

    # Ensure consistent formatting around ANSWER:
    text = re.sub(r"ANSWER:\s*", "ANSWER: ", text)

    return text


def parse_questions(text: str, source_file: str) -> List[Question]:
    """Parse the document text into structured Question objects."""
    # First preprocess the text
    text = preprocess_text(text)

    # Split on TOSS-UP and BONUS headers
    # Updated pattern that includes ANSWER section in each match and handles various formats
    pattern = r"(TOSS-UP|BONUS|VISUAL BONUS)\s*\n\s*(\d+)\)(.*?ANSWER:.*?)(?=(?:\n\s*(?:TOSS-UP|BONUS|VISUAL BONUS|HIGH SCHOOL|MIDDLE SCHOOL|~~~))|(?:\n_+\n)|(?:\n\n)|$)"
    matches = re.finditer(pattern, text, re.DOTALL)

    questions = []

    for match in matches:
        q_number = match.group(2).strip()  # Question number
        content = match.group(3).strip()  # Rest of content including ANSWER

        # Try to find subject and type using different patterns

        # Pattern 1: Standard format with dash separator
        subject_type_pattern1 = (
            r"([\w\s]+)\s*[–—|–|-]\s*((?:Multiple Choice|Short Answer))"
        )

        # Pattern 2: Format with subject in all caps and no dash
        subject_type_pattern2 = (
            r"([A-Z]+(?:\s+[A-Z]+)*)\s+(Multiple Choice|Short Answer)"
        )

        subject_type_match = re.search(subject_type_pattern1, content, re.IGNORECASE)
        if not subject_type_match:
            subject_type_match = re.search(
                subject_type_pattern2, content, re.IGNORECASE
            )

        if not subject_type_match:
            print(
                f"Warning: Could not parse subject and type for question {q_number} in content: {content[:50]}..."
            )
            continue  # Skip if we can't parse subject and type

        subject = subject_type_match.group(1).strip()
        q_type = subject_type_match.group(2).strip()

        # Extract question text and answer
        question_answer_pattern = r"(?:Multiple Choice|Short Answer|Multiple choice|Short answer)(.*?)ANSWER:\s*(.*?)$"
        qa_match = re.search(question_answer_pattern, content, re.DOTALL)

        if not qa_match:
            print(
                f"Warning: Could not parse question text and answer for question {q_number} in content: {content[:50]}..."
            )
            # Try a more general pattern that doesn't rely on Multiple Choice/Short Answer
            general_qa_pattern = r"(.*?)ANSWER:\s*(.*?)$"
            qa_match = re.search(general_qa_pattern, content, re.DOTALL)

            if not qa_match:
                continue  # Skip if we can't parse even with the more general pattern

        q_text = qa_match.group(1).strip()
        answer_text = qa_match.group(2).strip()

        # Parse the answer
        primary, alternates = parse_answer(answer_text)

        # Create the answers list
        answers = [Answer(text=primary, is_primary=True)]
        for alt in alternates:
            answers.append(Answer(text=alt, is_primary=False))

        questions.append(
            Question(
                id=None,
                subject=subject,
                type=q_type,
                text=q_text,
                answers=answers,
                source_file=source_file,
            )
        )

    return questions


def parse_answer(answer_text: str) -> Tuple[str, List[str]]:
    """Parse the answer text to extract primary and alternate answers."""
    # Clean up the answer text
    answer_text = answer_text.strip()

    # Check for ACCEPT pattern (handles various formats)
    accept_pattern = r"\((?:ACCEPT:?|ALSO ACCEPT:?)(.*?)\)"
    accept_match = re.search(accept_pattern, answer_text, re.IGNORECASE)

    if accept_match:
        # Extract the primary answer (text before the ACCEPT clause)
        primary_text = answer_text[: accept_match.start()].strip()

        # Extract alternate answers
        accept_text = accept_match.group(1).strip()

        # Handle multiple accepts separated by commas, semicolons, or "OR"
        alternates = []
        for alt in re.split(r"[,;]\s*|\s+OR\s+", accept_text):
            if alt.strip():
                alternates.append(alt.strip())

        return primary_text, alternates

    # Check for DO NOT ACCEPT pattern
    do_not_pattern = r"\(?do not accept:?(.*?)\)?"
    do_not_match = re.search(do_not_pattern, answer_text, re.IGNORECASE)

    if do_not_match:
        # Return primary answer without the "do not accept" part
        primary_text = answer_text[: do_not_match.start()].strip()
        return primary_text, []

    # Handle special cases
    if re.search(r"\bALL\b", answer_text):
        return "ALL", []

    # If no explicit alternates, return just the primary
    return answer_text, []


def setup_database(db_path: str) -> sqlite3.Connection:
    """
    Initialize SQLite database with table structure for answer equivalence graph,
    including an FTS5 virtual table for full-text search on answers,
    with triggers matching documented examples for external content tables.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Enable foreign key constraints (good practice)
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Create tables for questions and answers
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY, -- Automatically aliases rowid, auto-increments
        source_file TEXT,       -- File where this question was FIRST seen
        subject TEXT,
        type TEXT,
        text TEXT NOT NULL UNIQUE COLLATE NOCASE -- Case-insensitive unique question text
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL, -- References the unique question
        source_file TEXT,             -- File where THIS answer instance appeared
        answer_text TEXT COLLATE NOCASE NOT NULL, -- Case-insensitive unique answer text
        is_primary BOOLEAN,
        FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
    )
    """)
    # Create an equivalence graph table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS answer_equivalents (
        group_id INTEGER NOT NULL,
        answer_id INTEGER NOT NULL,
        PRIMARY KEY (group_id, answer_id),
        FOREIGN KEY (answer_id) REFERENCES answers(id) ON DELETE CASCADE -- Consider cascade delete
    )
    """)

    # --- FTS Setup ---
    # Create the FTS5 virtual table for searching answer_text
    # 'content=answers' links it to the answers table
    # 'content_rowid=id' specifies that the 'rowid' in the FTS table corresponds to the 'id' in the answers table
    # We include 'answer_text' as the column to be indexed and searched.
    cursor.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS answers_fts USING fts5(
        answer_text,
        content='answers',
        content_rowid='id',
        tokenize = "unicode61"
    )
    """)

    # Create triggers to keep the FTS table synchronized with the answers table
    # Using the syntax recommended in the SQLite documentation for external content tables.

    # Trigger after inserting a row into answers
    # This remains the same standard INSERT.
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS answers_ai AFTER INSERT ON answers BEGIN
        INSERT INTO answers_fts (rowid, answer_text) VALUES (new.id, new.answer_text);
    END;
    """)

    # Trigger after deleting a row from answers
    # Use the special 'delete' command via INSERT for external content tables.
    # We pass the 'old' values, though for 'delete' only the rowid matters.
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS answers_ad AFTER DELETE ON answers BEGIN
        INSERT INTO answers_fts (answers_fts, rowid, answer_text) VALUES ('delete', old.id, old.answer_text);
    END;
    """)

    # Trigger after updating a row in answers
    # Use the 'delete' command for the old row, then insert the new row.
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS answers_au AFTER UPDATE ON answers BEGIN
        INSERT INTO answers_fts (answers_fts, rowid, answer_text) VALUES ('delete', old.id, old.answer_text);
        INSERT INTO answers_fts (rowid, answer_text) VALUES (new.id, new.answer_text);
    END;
    """)
    # --- End FTS Setup ---

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_answers_question ON answers(question_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_answers_text_q_id ON answers(answer_text, question_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_equivalents_group ON answer_equivalents(group_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_equivalents_answer ON answer_equivalents(answer_id)"
    )

    conn.commit()
    return conn


def process_document(file_path: Path, db_conn: sqlite3.Connection) -> int:
    """Process a document and store its questions and answers in the database."""
    # Extract text from document
    if file_path.suffix.lower() == ".docx":
        text = extract_text_from_docx(file_path)
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

    # Parse questions
    questions = parse_questions(preprocess_text(text), str(file_path))

    # Store in database
    cursor = db_conn.cursor()
    processed_count = 0  # Keep track of successfully processed questions

    for question in questions:
        # Attempt to insert the question
        cursor.execute(
            """INSERT OR IGNORE INTO questions (source_file, subject, type, text)
               VALUES (?, ?, ?, ?)""",
            (
                question.source_file,  # Source where it was first encountered (or attempted)
                question.subject,
                question.type,
                question.text,
            ),
        )

        current_question_id = None
        if cursor.rowcount > 0:
            # Insert was successful, get the new ID
            current_question_id = cursor.lastrowid
            print(
                f"Inserted new question (ID: {current_question_id}) from {question.source_file}"
            )
        else:
            # Insert was ignored (question text already exists), so we probably processed it before.
            # We can just continue to the next question.
            continue

        # Assign the determined ID back to the question object (optional, but good practice)
        question.id = current_question_id

        # --- Insert Answers using the determined ID ---
        answer_ids = []
        for answer in question.answers:
            # Insert new answer, referencing the correct question_id
            # Note: We still store the source_file for *this answer instance*
            try:
                cursor.execute(
                    """INSERT INTO answers (question_id, source_file, answer_text, is_primary)
                       VALUES (?, ?, ?, ?)""",
                    (
                        current_question_id,
                        question.source_file,
                        answer.text,
                        answer.is_primary,
                    ),
                )
                answer_id = cursor.lastrowid
                answer_ids.append(answer_id)
            except sqlite3.IntegrityError as e:
                print(
                    f"{Fore.YELLOW}Warning: Could not insert answer '{answer.text}' for question ID {current_question_id}. Reason: {e}{Style.RESET_ALL}"
                )

        # --- Build answer equivalence relationships ---
        if len(answer_ids) > 1:
            group_id = None

            for answer_id in answer_ids:
                cursor.execute(
                    "SELECT group_id FROM answer_equivalents WHERE answer_id = ?",
                    (answer_id,),
                )
                result = cursor.fetchone()
                if result:
                    group_id = result[0]
                    break
            if group_id is None:
                cursor.execute(
                    "SELECT COALESCE(MAX(group_id), 0) + 1 FROM answer_equivalents"
                )
                group_id = cursor.fetchone()[0]
            for answer_id in answer_ids:
                cursor.execute(
                    "INSERT OR IGNORE INTO answer_equivalents (group_id, answer_id) VALUES (?, ?)",
                    (group_id, answer_id),
                )
        processed_count += 1  # Increment only if we successfully processed the question and its answers

    db_conn.commit()
    return processed_count


def find_questions_by_answer(
    conn: sqlite3.Connection,
    answer_text: str,
    use_fts: bool = True,
    max_questions_per_answer: int = 5,
) -> List[Dict]:
    """
    Find all answers matching or equivalent to the search term, then group
    questions by each answer text, showing how many questions use each answer.
    Returns a list of answer groups, each containing up to N sample questions.
    """
    cursor = conn.cursor()

    # Find initial matching answer IDs (same as before)
    initial_answer_ids = []
    if use_fts:
        cursor.execute(
            "SELECT rowid FROM answers_fts WHERE answers_fts MATCH ? ORDER BY bm25(answers_fts)",
            (f'"{answer_text}"',),
        )
        initial_answer_ids = [row[0] for row in cursor.fetchall()]
    else:
        cursor.execute("SELECT id FROM answers WHERE answer_text = ?", (answer_text,))
        initial_answer_ids = [row[0] for row in cursor.fetchall()]

    if not initial_answer_ids:
        return []

    # Find all groups containing these initial answers
    all_relevant_answer_ids = set(initial_answer_ids)
    placeholders = ",".join(["?"] * len(initial_answer_ids))
    cursor.execute(
        f"""
        SELECT DISTINCT group_id
        FROM answer_equivalents
        WHERE answer_id IN ({placeholders})
        """,
        initial_answer_ids,
    )
    group_ids = [row[0] for row in cursor.fetchall()]

    # Get all answer IDs from these groups
    if group_ids:
        placeholders = ",".join(["?"] * len(group_ids))
        cursor.execute(
            f"""
            SELECT answer_id
            FROM answer_equivalents
            WHERE group_id IN ({placeholders})
            """,
            group_ids,
        )
        for row in cursor.fetchall():
            all_relevant_answer_ids.add(row[0])

    placeholders = ",".join(["?"] * len(all_relevant_answer_ids))
    cursor.execute(
        f"""
        SELECT 
            a.answer_text,
            a.is_primary,
            q.id as question_id,
            q.subject,
            q.type,
            q.text as question_text,
            q.source_file
        FROM answers a
        JOIN questions q ON a.question_id = q.id
            AND q.type = 'Short Answer'
        WHERE a.id IN ({placeholders})
        -- Exclude list-style questions
        AND q.text NOT LIKE '%_)%'
        -- Exclude the exact answer text to avoid duplicates
        AND a.answer_text != (?) COLLATE NOCASE
        ORDER BY a.answer_text, a.is_primary DESC
        """,
        list(all_relevant_answer_ids)
        + [answer_text.upper().strip()],  # Ensure case-insensitive match
    )

    # Group by answer text
    answers_dict = {}
    for row in cursor.fetchall():
        answer_text, is_primary, q_id, subject, q_type, q_text, source_file = row
        answer_text = answer_text.upper().strip()

        if answer_text not in answers_dict:
            answers_dict[answer_text] = {
                "text": answer_text,
                "questions": [],
                "is_primary_somewhere": False,
            }

        # Mark if this answer is primary in any question
        if is_primary:
            answers_dict[answer_text]["is_primary_somewhere"] = True

        # Add the question if we haven't reached max_questions_per_answer
        question_info = {
            "id": q_id,
            "subject": subject,
            "type": q_type,
            "text": q_text,
            "source_file": source_file,
        }

        # Check if this question is already in the list for this answer
        if not any(q["id"] == q_id for q in answers_dict[answer_text]["questions"]):
            if len(answers_dict[answer_text]["questions"]) < max_questions_per_answer:
                answers_dict[answer_text]["questions"].append(question_info)

    # Calculate total question count for each answer
    # Get all counts in a single query with GROUP BY
    cursor.execute(
        """
        SELECT a.answer_text, COUNT(DISTINCT q.id) as question_count
        FROM answers a
        JOIN questions q ON a.question_id = q.id
        WHERE a.answer_text IN ({}) COLLATE NOCASE
        AND q.type = 'Short Answer'
        AND q.text NOT LIKE '%_)%'
        GROUP BY a.answer_text
    """.format(",".join("?" * len(answers_dict))),
        list(answers_dict.keys()),
    )

    # Update the dictionary with counts
    for answer_text, count in cursor.fetchall():
        if answer_text.upper().strip() in answers_dict:
            answers_dict[answer_text.upper().strip()]["total_question_count"] = count

    # Set default count of 0 for any answers that weren't returned in the query
    for answer_text in answers_dict:
        if "total_question_count" not in answers_dict[answer_text.upper().strip()]:
            answers_dict[answer_text.upper().strip()]["total_question_count"] = 0

    # Convert to list and sort by total question count (descending)
    results = list(answers_dict.values())
    results.sort(key=lambda x: x["total_question_count"], reverse=True)

    return results


def print_answer_groups_colorized(results: List[Dict]):
    """Print results grouped by answer text in a color-coded format."""
    if not results:
        print("No equivalent answers found.")
        return

    total_answers = len(results)

    print(f"Found {Fore.GREEN}{total_answers}{Style.RESET_ALL} unique answer texts:")

    for answer_group in results:
        primary_marker = (
            f" {Fore.RED}(PRIMARY){Style.RESET_ALL}"
            if answer_group["is_primary_somewhere"]
            else ""
        )
        total_questions = answer_group["total_question_count"]
        displayed_questions = len(answer_group["questions"])

        print(f"\n{Fore.GREEN}{answer_group['text']}{Style.RESET_ALL}{primary_marker}")
        print(f"Appears in {Fore.YELLOW}{total_questions}{Style.RESET_ALL} questions")

        if displayed_questions < total_questions:
            print(f"Showing {displayed_questions} of {total_questions} questions:")

        for question in answer_group["questions"]:
            print(
                f"  - {Fore.CYAN}[{question['subject']}]{Style.RESET_ALL} {question['text'][:80]}..."
            )
            print(f"    Source: {question['source_file']}")

        if displayed_questions < total_questions:
            print(f"    ... and {total_questions - displayed_questions} more questions")


def print_answer_groups_json(results: List[Dict]):
    """Print answer groups in JSON format."""
    import json

    print(json.dumps(results, indent=2, ensure_ascii=False))
