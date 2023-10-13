import argparse
from pathlib import Path


from .assign import EditedQuestions
from .classes import Subject
from .tables import RawQuestions
from .yamlparsers import ParsedQuestionSpec


def make(args):
    path = Path(args.path).with_suffix(".docx")
    if args.subj is not None:
        args.subj = Subject.from_string(args.subj).value
    RawQuestions.make(
        nrows=args.rows, name=args.name, subj=args.subj, set=args.set
    ).format(verbose=False).save(path)


def format(args):
    questions = RawQuestions.from_docx_path(args.path)
    questions.format(
        force_capitalize=args.capitalize, line_after_stem=args.line_after_stem
    )
    questions.save(args.path)


def assign(args):
    questions = EditedQuestions.from_docx_path(args.path)
    spec = ParsedQuestionSpec.from_yaml_path(args.config)

    questions.assign(spec, dry_run=args.dry_run)
    questions.save(args.path)


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

    args = argparser.parse_args()
    args.func(args)
