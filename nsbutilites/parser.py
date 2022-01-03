import docx2txt
import argparse
import os


def validate_path(path_string: str) -> str:
    """Validates that incoming path exists.

    Parameters
    ----------
    path_string : str

    Returns
    -------
    path_string

    Raises
    ------
    FileNotFoundError

    """
    if os.path.exists(path_string):
        return path_string
    else:
        raise FileNotFoundError(f"No such file: {path_string}")


if __name__ == "__main__":

    argparser = argparse.ArgumentParser(
        description="Parser for Science Bowl .docx files."
    )
    argparser.add_argument(
        "path",
        metavar="path",
        type=str,
        help="path to the Science Bowl docx file",
    )

    args = argparser.parse_args()

    path_to_data = validate_path(args.path)

    raw_text = docx2txt.process(path_to_data).split()
