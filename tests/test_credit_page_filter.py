import os
import sys
import tempfile
import unittest
from unittest.mock import call, patch

from PIL import Image, ImageDraw
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

import merge_manga


def make_reference_image(size=(240, 320)):
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 25, 130, 90), fill="black")
    draw.ellipse((100, 150, 220, 270), fill="gray")
    draw.line((15, 300, 225, 110), fill="black", width=8)
    return image


class CreditPageFilterTests(unittest.TestCase):
    def test_load_credit_images_recursively(self):
        with tempfile.TemporaryDirectory() as directory:
            nested = os.path.join(directory, "nested")
            os.makedirs(nested)
            make_reference_image().save(os.path.join(directory, "top.png"))
            make_reference_image().save(os.path.join(nested, "nested.jpg"))

            images = merge_manga.load_credit_images(directory)

        self.assertEqual(len(images), 2)
        self.assertTrue(all(image.mode == "L" for image in images))
        self.assertTrue(all(image.size == merge_manga.CREDIT_MATCH_SIZE for image in images))

    def test_matching_uses_spatial_content_not_grayscale_histogram(self):
        reference = make_reference_image()
        unrelated = Image.new("RGB", reference.size, "white")
        draw = ImageDraw.Draw(unrelated)
        draw.rectangle((20, 25, 130, 90), fill="gray")
        draw.ellipse((100, 150, 220, 270), fill="black")
        draw.line((15, 110, 225, 300), fill="black", width=8)

        self.assertTrue(merge_manga.is_credit_page(reference.resize((900, 1200)), [reference]))
        self.assertFalse(merge_manga.is_credit_page(unrelated, [reference]))
        self.assertFalse(
            merge_manga.is_credit_page(
                Image.new("RGB", reference.size, "white"), [reference]
            )
        )

    def test_removes_matching_page_anywhere_without_removing_text_heavy_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            pdf_path = os.path.join(directory, "input.pdf")
            document = canvas.Canvas(pdf_path)
            for page_number in range(18):
                if page_number == 0:
                    document.drawString(40, 750, "credit " * 40)
                document.showPage()
            document.save()

            reference = make_reference_image()
            rendered_pages = [
                Image.new("RGB", reference.size, "white") for _ in range(18)
            ]
            rendered_pages[16] = reference

            def render_batch(_path, first_page, last_page, **_kwargs):
                return rendered_pages[first_page - 1:last_page]

            with patch(
                "merge_manga.convert_from_path", side_effect=render_batch
            ) as render_mock:
                cleaned_path, deleted_count = merge_manga.remove_credit_pages(
                    pdf_path, [reference]
                )

            try:
                self.assertNotEqual(cleaned_path, pdf_path)
                self.assertEqual(deleted_count, 1)
                self.assertEqual(len(PdfReader(cleaned_path).pages), 17)
                self.assertEqual(
                    render_mock.call_args_list,
                    [
                        call(
                            pdf_path,
                            dpi=80,
                            poppler_path=merge_manga.POPPLER_PATH,
                            first_page=1,
                            last_page=16,
                        ),
                        call(
                            pdf_path,
                            dpi=80,
                            poppler_path=merge_manga.POPPLER_PATH,
                            first_page=17,
                            last_page=18,
                        ),
                    ],
                )
            finally:
                if cleaned_path != pdf_path:
                    os.remove(cleaned_path)

    def test_failed_merge_never_moves_source_to_trash(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = os.path.join(directory, "Series ตอนที่ 1.pdf")
            document = canvas.Canvas(source_path)
            document.drawString(40, 750, "original source")
            document.save()
            with open(source_path, "rb") as source:
                original_bytes = source.read()

            class FailingMerger:
                def append(self, _path):
                    pass

                def write(self, _path):
                    raise OSError("simulated disk write failure")

                def close(self):
                    pass

            with patch.object(sys, "argv", ["merge_manga.py", source_path]), patch(
                "merge_manga.load_credit_images", return_value=[]
            ), patch("merge_manga.PdfMerger", FailingMerger), patch(
                "merge_manga.send2trash"
            ) as trash_mock:
                merge_manga.merge_manga()

            self.assertTrue(os.path.exists(source_path))
            with open(source_path, "rb") as source:
                self.assertEqual(source.read(), original_bytes)
            self.assertFalse(
                os.path.exists(
                    os.path.join(directory, "Series ตอนที่ 1 (2).pdf")
                )
            )
            trash_mock.assert_not_called()

    def test_successful_merge_avoids_source_and_existing_output_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = os.path.join(directory, "Series ตอนที่ 1.pdf")
            existing_output = os.path.join(directory, "Series ตอนที่ 1 (2).pdf")
            document = canvas.Canvas(source_path)
            document.drawString(40, 750, "original source")
            document.save()
            with open(source_path, "rb") as source:
                original_bytes = source.read()
            with open(existing_output, "wb") as output:
                output.write(b"existing output must not be overwritten")

            with patch.object(sys, "argv", ["merge_manga.py", source_path]), patch(
                "merge_manga.load_credit_images", return_value=[]
            ), patch("merge_manga.send2trash") as trash_mock:
                merge_manga.merge_manga()

            merged_path = os.path.join(directory, "Series ตอนที่ 1 (3).pdf")
            self.assertTrue(os.path.exists(source_path))
            with open(source_path, "rb") as source:
                self.assertEqual(source.read(), original_bytes)
            self.assertEqual(
                len(PdfReader(merged_path).pages),
                2,
            )
            with open(existing_output, "rb") as output:
                self.assertEqual(
                    output.read(), b"existing output must not be overwritten"
                )
            trash_mock.assert_called_once_with(source_path)

    def test_size_mismatch_rejects_merge_and_keeps_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = os.path.join(directory, "source.pdf")
            output_path = os.path.join(directory, "merged.pdf")
            document = canvas.Canvas(source_path)
            document.drawString(40, 750, "source page")
            document.save()

            class OversizedMerger:
                def __init__(self):
                    self.paths = []

                def append(self, path):
                    self.paths.append(path)

                def write(self, path):
                    writer = PdfWriter()
                    for source in self.paths:
                        reader = PdfReader(source)
                        for page in reader.pages:
                            writer.add_page(page)
                    writer.write(path)
                    with open(path, "ab") as output:
                        output.write(b" " * 100_000)

                def close(self):
                    pass

            with patch("merge_manga.PdfMerger", OversizedMerger):
                with self.assertRaisesRegex(ValueError, "ต่างจากขนาดรวม"):
                    merge_manga.write_and_validate_merge([source_path], output_path)

            self.assertTrue(os.path.exists(source_path))
            self.assertFalse(os.path.exists(output_path))
            self.assertEqual(os.listdir(directory), ["source.pdf"])


if __name__ == "__main__":
    unittest.main()
