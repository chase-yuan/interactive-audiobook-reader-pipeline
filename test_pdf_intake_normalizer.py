import tempfile
import unittest
import zipfile
from pathlib import Path

from pdf_intake_normalizer import sanitize_text, convert_pdf_to_epub
try:
    import pypdf
except ImportError:
    pypdf = None


class PdfIntakeNormalizerTests(unittest.TestCase):
    def test_sanitize_text(self):
        # Soft hyphen wrap
        wrapped = "This is a philo- \n sophical question."
        self.assertEqual(sanitize_text(wrapped), "This is a philosophical question.")

        # Unicode spaces and returns
        raw = "Hello\r\nworld\u2003test"
        self.assertEqual(sanitize_text(raw), "Hello\nworld test")

    @unittest.skipIf(pypdf is None, "pypdf not available")
    def test_convert_pdf_to_epub_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pdf_path = tmp_path / "sample.pdf"
            epub_path = tmp_path / "output.epub"

            # Create a minimal 2-page PDF
            writer = pypdf.PdfWriter()
            writer.add_blank_page(width=200, height=200)
            writer.add_blank_page(width=200, height=200)
            writer.add_outline_item("Chapter 1", 0)
            writer.add_outline_item("Chapter 2", 1)
            with pdf_path.open("wb") as f:
                writer.write(f)

            convert_pdf_to_epub(pdf_path, epub_path, title_override="Test PDF Book", author_override="Author")

            self.assertTrue(epub_path.is_file())
            self.assertGreater(epub_path.stat().st_size, 500)

            # Check EPUB contents
            with zipfile.ZipFile(epub_path, "r") as zf:
                names = zf.namelist()
                self.assertIn("mimetype", names)
                self.assertIn("META-INF/container.xml", names)
                self.assertIn("OEBPS/content.opf", names)
                self.assertIn("OEBPS/toc.ncx", names)


if __name__ == "__main__":
    unittest.main()
