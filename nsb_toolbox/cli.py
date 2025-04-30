import argparse
from pathlib import Path

from colorama import Fore, Style, init


def make(args):
    from .classes import Subject
    from .tables import RawQuestions

    path = Path(args.path).with_suffix(".docx")
    if args.subj is not None:
        args.subj = Subject.from_string(args.subj).value
    RawQuestions.make(
        nrows=args.rows, name=args.name, subj=args.subj, set=args.set
    ).format(verbose=False).save(path)


def format(args):
    from .tables import RawQuestions

    questions = RawQuestions.from_docx_path(args.path)
    questions.format(
        force_capitalize=args.capitalize, line_after_stem=args.line_after_stem
    )
    questions.save(args.path)


def assign(args):
    from .assign import EditedQuestions
    from .yamlparsers import ParsedQuestionSpec

    questions = EditedQuestions.from_docx_path(args.path)
    spec = ParsedQuestionSpec.from_yaml_path(args.config)

    questions.assign(spec, dry_run=args.dry_run)
    questions.save(args.path)


def db_ingest(args):
    from .db import process_document, setup_database

    db_path = Path(args.db_path).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Ingesting questions from {args.path} into database at {db_path}")

    conn = setup_database(str(db_path))

    target_path = Path(args.path)

    if target_path.is_dir():
        # Process all files in directory
        total_questions = 0
        for file_path in target_path.rglob("*.*"):
            if file_path.suffix.lower() in [".txt", ".docx"]:
                try:
                    count = process_document(file_path, conn)
                    print(f"Processed {file_path.name}: {count} questions")
                    total_questions += count
                except Exception as e:
                    print(
                        f"{Fore.RED}Error processing {file_path.name}: {e}{Style.RESET_ALL}"
                    )
        print(
            f"{Fore.GREEN}Total questions ingested: {total_questions}{Style.RESET_ALL}"
        )
    else:
        # Process single file
        try:
            count = process_document(target_path, conn)
            print(f"Processed {target_path.name}: {count} questions")
        except Exception as e:
            print(
                f"{Fore.RED}Error processing {target_path.name}: {e}{Style.RESET_ALL}"
            )

    conn.close()


def db_search(args):
    from .db import (
        find_questions_by_answer,
        print_answer_groups_colorized,
        print_answer_groups_json,
        setup_database,
    )

    db_path = Path(args.db_path).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = setup_database(str(db_path))
    results = find_questions_by_answer(conn, args.answer, not args.exact)

    if args.json:
        print_answer_groups_json(results)
    else:
        print_answer_groups_colorized(results)

    conn.close()


def main():
    init(autoreset=True)  # Initialize colorama for Windows compatibility

    argparser = argparse.ArgumentParser(
        description="Utilities for managing Science Bowl .docx files."
    )

    # Base parsers for sharing arguments
    path_parser = argparse.ArgumentParser(add_help=False)
    path_parser.add_argument(
        "path",
        metavar="path",
        type=str,
        help="path to the Science Bowl docx file",
    )

    # Create a db_options parser for database-related arguments
    db_options_parser = argparse.ArgumentParser(add_help=False)
    db_options_parser.add_argument(
        "--db-path",
        type=Path,
        default="~/.nsb/science_bowl_questions.db",
        help="Path to the SQLite database file (default: ~/science_bowl_questions.db)",
    )

    subparsers = argparser.add_subparsers(title="subcommands")
    format_parser = subparsers.add_parser(
        "format", parents=[path_parser], help="format a Science Bowl file"
    )
    format_parser.add_argument(
        "--capitalize",
        action="store_true",
        help="force all answer lines to be capitalized",
    )
    format_parser.add_argument(
        "--line-after-stem",
        action="store_true",
        help="adds a line after the stem in multiple choice questions",
    )
    format_parser.set_defaults(func=format)

    make_parser = subparsers.add_parser(
        "make", parents=[path_parser], help="make a Science Bowl table"
    )
    make_parser.add_argument(
        "rows",
        metavar="rows",
        type=int,
        help="number of rows in output table",
    )
    make_parser.add_argument(
        "-n",
        "--name",
        action="store",
        type=str,
        required=False,
        help="Last, First name of author",
    )

    make_parser.add_argument(
        "-st",
        "--set",
        choices=["HSR", "HSN", "MSR", "MSN"],
        required=False,
        help="Set",
    )

    make_parser.add_argument(
        "-su",
        "--subj",
        choices=["B", "C", "P", "M", "ES", "EN"],
        required=False,
        help="Subject",
    )

    make_parser.set_defaults(func=make)

    assign_parser = subparsers.add_parser(
        "assign", parents=[path_parser], help="assign Science Bowl questions to rounds"
    )
    assign_parser.add_argument(
        "-c",
        "--config",
        action="store",
        type=Path,
        required=True,
        help="Path to yaml config",
    )
    assign_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="performs assignment, but doesn't save results",
    )
    assign_parser.set_defaults(func=assign)

    db_subparsers = subparsers.add_parser(
        "db", help="database operations for Science Bowl questions"
    ).add_subparsers(title="database commands")

    ingest_parser = db_subparsers.add_parser(
        "ingest",
        help="ingest Science Bowl questions from a docx file into the database",
        parents=[path_parser, db_options_parser],
    )
    ingest_parser.set_defaults(func=db_ingest)

    search_parser = db_subparsers.add_parser(
        "search",
        help="search Science Bowl questions database",
        parents=[db_options_parser],
    )
    search_parser.add_argument(
        "answer",
        type=str,
        help="Answer to search for in the database (case-insensitive)",
    )
    search_parser.add_argument(
        "--exact",
        action="store_true",
        help="Search for exact match of the answer",
    )
    search_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )
    search_parser.set_defaults(func=db_search)

    # Parse and execute
    args = argparser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        argparser.print_help()
