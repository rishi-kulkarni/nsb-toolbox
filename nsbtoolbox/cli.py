import argparse
from .importers import validate_path
from .tables import format_table, initialize_table
from docx import Document
from .classes import Subject
from pathlib import Path


def make(args):
    path = Path(args.path).with_suffix(".docx")
    if args.subj is not None:
        args.subj = Subject.from_string(args.subj).value
    initialize_table(
        nrows=args.rows, name=args.name, subj=args.subj, set=args.set, path=path
    )


def format(args):
    path_to_data = validate_path(args.path)
    doc = Document(path_to_data)

    format_table(doc)
    doc.save(path_to_data)


def main():
    argparser = argparse.ArgumentParser(
        description="Utilities for managing Science Bowl .docx files."
    )
    path_parser = argparse.ArgumentParser(add_help=False)
    path_parser.add_argument(
        "path",
        metavar="path",
        type=str,
        help="path to the Science Bowl docx file",
    )

    subparsers = argparser.add_subparsers(title="subcommands")
    format_parser = subparsers.add_parser(
        "format", parents=[path_parser], help="format a Science Bowl file"
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

    args = argparser.parse_args()
    args.func(args)
