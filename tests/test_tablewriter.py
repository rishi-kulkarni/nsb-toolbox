import nsbtoolbox
import unittest

from nsbtoolbox import tablewriter

from docx.shared import Pt
from docx import Document


class TestInitializeTable(unittest.TestCase):
    def _check_table_characteristics(self, document, nrows):

        font = document.styles["Normal"].font
        self.assertEqual(font.name, "Times New Roman")
        self.assertEqual(font.size, Pt(11))

        self.assertEqual(len(document.tables), 1)
        table = document.tables[0]
        self.assertEqual(len(table.rows), nrows + 1)

        for idx, cell in enumerate(table.rows[0].cells):
            self.assertAlmostEqual(
                cell.width.inches, tablewriter.COL_WIDTHS[idx], places=2
            )

    def test_intialize_table(self):
        _nrows = (0, 90, 150, 180)
        for nrow in _nrows:
            document = tablewriter.initialize_table(nrow)
            self._check_table_characteristics(document, nrow)
