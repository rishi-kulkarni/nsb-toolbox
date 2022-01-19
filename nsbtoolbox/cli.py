import argparse
from .importers import validate_path
from .tables import format_table, initialize_table
from docx import Document


def make(args):
    initialize_table(nrows=args.rows, path=args.path)


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
        "-r",
        "--rows",
        action="store",
        type=int,
        required=True,
        help="number of rows in output table",
    )
    make_parser.set_defaults(func=make)

    args = argparser.parse_args()
    args.func(args)
