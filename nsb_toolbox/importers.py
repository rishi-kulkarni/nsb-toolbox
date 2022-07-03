from pathlib import Path
from typing import Union, Dict

from docx.document import Document as DocClass
from docx import Document
import yaml


def validate_path(path_string: Union[str, Path]) -> Path:
    """Validates that incoming path exists.

    Parameters
    ----------
    path_string : str

    Returns
    -------
    path: Path

    Raises
    ------
    FileNotFoundError

    """
    path = Path(path_string)
    if path.exists():
        return path
    else:
        raise FileNotFoundError(f"No such file: {path_string}")


def load_yaml(path: Union[Path, str]) -> Dict:
    """Parses a yaml files and returns a YAML representation object.

    Parameters
    ----------
    path : Path

    Returns
    -------
    Dict

    """
    path = validate_path(path)

    with open(path) as file:
        data = yaml.safe_load(file)
        return data


def load_doc(path: Union[Path, str]) -> DocClass:
    path = validate_path(path)
    return Document(path)
