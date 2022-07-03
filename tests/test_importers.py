from pathlib import Path
from unittest import TestCase

from nsb_toolbox.importers import load_yaml

data_dir = Path(__file__).parent / "test_data"


class TestLoadYAML(TestCase):
    def test_str_path(self):

        self.assertIsInstance(load_yaml(str(data_dir / "assign.yaml")), dict)

    def test_Path_path(self):

        self.assertIsInstance(load_yaml(data_dir / "assign.yaml"), dict)

    def test_exception(self):

        with self.assertRaises(FileNotFoundError) as ex:
            load_yaml(data_dir / "does_not_exist.yaml"), dict
        self.assertIn("No such file", str(ex.exception))
