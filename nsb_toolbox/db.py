import re
import docx
import sqlite3
from dataclasses import dataclass
from typing import List, Dict, Tuple
from pathlib import Path
from colorama import init, Fore, Style


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
    doc = docx.Document(file_path)
    return "\n".join(para.text for para in doc.paragraphs)


def parse_questions(text: str, source_file: str) -> List[Question]:
    """Parse the document text into structured Question objects."""
    # Split on TOSS-UP and BONUS headers
    pattern = r"(TOSS-UP|BONUS|VISUAL BONUS)\s*\n\s*(\d+)\)(.*?)(?=(?:\n\s*(?:TOSS-UP|BONUS|VISUAL BONUS))|(?:\n\s*~{3,})|$)"
    matches = re.finditer(pattern, text, re.DOTALL)

    questions = []

    for match in matches:
        content = match.group(3).strip()  # Rest of the content

        # Extract subject and type
        subject_type_pattern = r"([\w\s]+)\s*–\s*((?:Multiple Choice|Short Answer))"
        subject_type_match = re.search(subject_type_pattern, content)

        if not subject_type_match:
            continue  # Skip if we can't parse subject and type

        subject = subject_type_match.group(1).strip()
        q_type = subject_type_match.group(2).strip()

        # Extract question text and answer
        question_answer_pattern = (
            r"(?:Multiple Choice|Short Answer).*?(.*?)ANSWER:\s*(.*?)$"
        )
        qa_match = re.search(question_answer_pattern, content, re.DOTALL)

        if not qa_match:
            continue  # Skip if we can't parse question text and answer

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
        text TEXT NOT NULL UNIQUE -- Ensures question text is unique
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL, -- References the unique question
        source_file TEXT,             -- File where THIS answer instance appeared
        answer_text TEXT,
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
    questions = parse_questions(text, str(file_path))

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


def find_equivalent_answers(
    conn: sqlite3.Connection,
    answer_text: str,
    use_fts: bool = True,
) -> List[Dict]:
    """
    Find all questions with answers equivalent (based on grouping) to those
    matching the given answer text, using FTS5 for searching.
    Retrieves all answers within the found equivalence groups.
    """
    cursor = conn.cursor()
    initial_answer_ids = []  # Renamed for clarity

    # --- Find initial matching answer IDs ---
    if use_fts:
        query = """
            SELECT rowid FROM answers_fts
            WHERE answers_fts MATCH ?
            ORDER BY bm25(answers_fts)
        """
        params = (f'"{answer_text}"',)
        cursor.execute(query, params)
        initial_answer_ids = [row[0] for row in cursor.fetchall()]
    else:
        cursor.execute("SELECT id FROM answers WHERE answer_text = ?", (answer_text,))
        initial_answer_ids = [row[0] for row in cursor.fetchall()]

    if not initial_answer_ids:
        return []

    # --- Find all groups containing these initial answers ---
    placeholders_answers = ",".join(["?"] * len(initial_answer_ids))
    cursor.execute(
        f"""
        SELECT DISTINCT group_id
        FROM answer_equivalents
        WHERE answer_id IN ({placeholders_answers})
        """,
        initial_answer_ids,
    )
    group_ids = [row[0] for row in cursor.fetchall()]

    # --- Handle case where initial answers might not be in any group ---
    # If no groups are found, maybe we should return the questions for the initial matches directly?
    # Or just the answers found initially? Let's refine this: Find ALL answer IDs,
    # either from groups OR the initial list if no groups were found.

    all_relevant_answer_ids = set(initial_answer_ids)  # Start with initial matches

    if group_ids:
        # Find ALL answer IDs belonging to any of these groups
        placeholders_groups = ",".join(["?"] * len(group_ids))
        cursor.execute(
            f"""
            SELECT answer_id
            FROM answer_equivalents
            WHERE group_id IN ({placeholders_groups})
            """,
            group_ids,
        )
        # Add all answers from the found groups to our set
        for row in cursor.fetchall():
            all_relevant_answer_ids.add(row[0])
    else:
        print("No explicit equivalence groups found for the initial answers.")
        # We already initialized all_relevant_answer_ids with the initial matches

    if not all_relevant_answer_ids:
        # This shouldn't happen if initial_answer_ids was populated, but defensive check
        print("Error: No relevant answer IDs found after group check.")
        return []

    # --- Fetch details for all relevant answers and their questions ---
    placeholders_all_answers = ",".join(["?"] * len(all_relevant_answer_ids))
    cursor.execute(
        f"""
        SELECT
            a.id as answer_id,
            a.answer_text,
            a.is_primary,
            a.question_id,
            a.source_file AS answer_source_file, -- Alias for clarity
            q.id as question_id_from_q, -- For verification if needed
            q.subject,
            q.type,
            q.text as question_text,
            q.source_file AS question_source_file -- Alias for clarity
        FROM answers a
        -- *** CORRECTED JOIN: Only on question_id ***
        JOIN questions q ON a.question_id = q.id
        WHERE a.id IN ({placeholders_all_answers})
        ORDER BY q.id, a.is_primary DESC, a.id -- Order by question, then primary answers first
        """,
        list(all_relevant_answer_ids),  # Pass the list of unique IDs
    )

    # Group results by question
    results = {}
    # No need for processed_answer_ids_in_question set anymore if we fetch unique IDs first

    for row in cursor.fetchall():
        (
            ans_id,
            ans_text,
            is_primary,
            q_id,
            ans_source_file,
            _,  # q_id_from_q (ignore)
            subject,
            q_type,
            q_text,
            q_source_file,  # Source file where question was first seen
        ) = row

        # *** CORRECTED Grouping Key: Use question ID ***
        question_key = q_id

        if question_key not in results:
            results[question_key] = {
                "id": q_id,
                "subject": subject,
                "type": q_type,
                "text": q_text,
                "source_file": q_source_file,  # Show the file where the question was first ingested
                "answers": [],
            }

        # Add answer details to the question's list
        results[question_key]["answers"].append(
            {
                "id": ans_id,
                "text": ans_text,
                "is_primary": bool(is_primary),
                "source_file": ans_source_file,  # Show file where this specific answer came from
            }
        )

    return list(results.values())


def main():
    """Command-line interface for the Science Bowl answer database tool."""
    import argparse

    # Initialize colorama
    init()

    parser = argparse.ArgumentParser(description="Science Bowl Answer Database Tool")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest questions from files")
    ingest_parser.add_argument("path", type=str, help="File or directory path")

    # Search command
    search_parser = subparsers.add_parser(
        "search", help="Search for equivalent answers"
    )
    search_parser.add_argument("answer", type=str, help="Answer text to search for")
    search_parser.add_argument(
        "--exact", action="store_true", help="Use exact matching"
    )
    search_parser.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )

    args = parser.parse_args()

    # Connect to database
    db_path = "science_bowl_answers.db"
    conn = setup_database(db_path)

    if args.command == "ingest":
        path = Path(args.path)

        if path.is_dir():
            # Process all files in directory
            total_questions = 0
            for file_path in path.rglob("*.*"):
                if file_path.suffix.lower() in [".txt", ".docx"]:
                    try:
                        count = process_document(file_path, conn)
                        print(f"Processed {file_path.name}: {count} questions")
                        total_questions += count
                    except Exception as e:
                        print(
                            f"{Fore.RED}Error processing {file_path.name}: {e}{Style.RESET_ALL}"
                        )

            print(f"Total: {total_questions} questions ingested")
        else:
            # Process single file
            count = process_document(path, conn)
            print(f"Processed {path.name}: {count} questions")

    elif args.command == "search":
        # New format - group by question
        results = find_equivalent_answers(conn, args.answer, not args.exact)

        if not results:
            print(f"No equivalent answers found for '{args.answer}'")
        else:
            print_results_colorized(results) if not args.json else print_results_json(
                results
            )

    conn.close()


def print_results_colorized(results: List[Dict]):
    """Print results in a color-coded format."""
    if not results:
        print("No equivalent answers found.")
        return

    total_questions = len(results)
    total_answers = sum(len(q["answers"]) for q in results)

    print(
        f"Found {Fore.GREEN}{total_answers}{Style.RESET_ALL} answers across {Fore.GREEN}{total_questions}{Style.RESET_ALL} questions:"
    )

    for question in results:
        print(f"\n{Fore.YELLOW}Question ID: {question['id']}{Style.RESET_ALL}")
        print(f"Subject: {question['subject']}, Type: {question['type']}")
        print(f"Text: {Fore.WHITE}{question['text'][:80]}...{Style.RESET_ALL}")
        print(f"Source File: {Fore.CYAN}{question['source_file']}{Style.RESET_ALL}")

        for answer in question["answers"]:
            primary_marker = (
                f" {Fore.RED}(PRIMARY){Style.RESET_ALL}" if answer["is_primary"] else ""
            )
            print(f"  - {Fore.GREEN}{answer['text']}{Style.RESET_ALL}{primary_marker}")


def print_results_json(results: List[Dict]):
    """Print results in JSON format."""
    import json

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
