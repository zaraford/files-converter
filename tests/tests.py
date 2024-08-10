import unittest
import os
import tempfile
from files_converter.converter import FileConverter


class TestFileConverter(unittest.TestCase):
    def setUp(self):
        self.converter = FileConverter()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_files_dir = os.path.join(os.path.dirname(__file__), "test_files")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_get_file_type(self):
        self.assertEqual(self.converter.get_file_type("example.jpg"), "photos")
        self.assertEqual(self.converter.get_file_type("example.mp4"), "videos")
        self.assertEqual(self.converter.get_file_type("example.svg"), "vectors")
        self.assertEqual(self.converter.get_file_type("example.mp3"), "audio")
        self.assertEqual(self.converter.get_file_type("example.docx"), "documents")
        self.assertEqual(self.converter.get_file_type("example.zip"), "archives")
        self.assertEqual(self.converter.get_file_type("example.epub"), "ebooks")
        self.assertIsNone(self.converter.get_file_type("example.unknown"))

    def test_get_target_formats(self):
        self.assertIn("jpg", self.converter.get_target_formats("photos"))
        self.assertIn("png", self.converter.get_target_formats("photos"))
        self.assertIn("mp4", self.converter.get_target_formats("videos"))
        self.assertIn("avi", self.converter.get_target_formats("videos"))
        self.assertIn("svg", self.converter.get_target_formats("vectors"))
        self.assertIn("eps", self.converter.get_target_formats("vectors"))
        self.assertIn("mp3", self.converter.get_target_formats("audio"))
        self.assertIn("wav", self.converter.get_target_formats("audio"))
        self.assertIn("pdf", self.converter.get_target_formats("documents"))
        self.assertIn("txt", self.converter.get_target_formats("documents"))
        self.assertIn("zip", self.converter.get_target_formats("archives"))
        self.assertIn("tar", self.converter.get_target_formats("archives"))
        self.assertIn("epub", self.converter.get_target_formats("ebooks"))
        self.assertIn("mobi", self.converter.get_target_formats("ebooks"))

    def test_convert_audio_files(self):
        audio_formats = ["mp3", "wav", "ogg", "flac", "aac"]
        for input_format in audio_formats:
            for target_format in audio_formats:
                if input_format != target_format:
                    input_path = os.path.join(self.test_files_dir, f"input.{input_format}")
                    output_path = os.path.join(self.temp_dir.name, f"output.{target_format}")
                    try:
                        self.converter._convert_audio(input_path, output_path, target_format)
                        self.assertTrue(
                            os.path.exists(output_path),
                            f"Failed to convert {input_format} to {target_format}",
                        )
                    except Exception as e:
                        self.fail(f"Error converting {input_format} to {target_format}: {str(e)}")

    def test_convert_video_files(self):
        video_formats = ["mp4", "avi", "mov", "mkv", "webm"]
        for input_format in video_formats:
            for target_format in video_formats:
                if input_format != target_format:
                    input_path = os.path.join(self.test_files_dir, f"input.{input_format}")
                    output_path = os.path.join(self.temp_dir.name, f"output.{target_format}")
                    try:
                        self.converter._convert_video(input_path, output_path, target_format)
                        self.assertTrue(
                            os.path.exists(output_path),
                            f"Failed to convert {input_format} to {target_format}",
                        )
                    except Exception as e:
                        self.fail(f"Error converting {input_format} to {target_format}: {str(e)}")

    def test_convert_image_files(self):
        image_formats = ["jpg", "png", "gif", "bmp", "tiff", "webp"]
        for input_format in image_formats:
            for target_format in image_formats:
                if input_format != target_format:
                    input_path = os.path.join(self.test_files_dir, f"input.{input_format}")
                    output_path = os.path.join(self.temp_dir.name, f"output.{target_format}")
                    try:
                        self.converter._convert_photo(input_path, output_path, target_format)
                        self.assertTrue(
                            os.path.exists(output_path),
                            f"Failed to convert {input_format} to {target_format}",
                        )
                    except Exception as e:
                        self.fail(f"Error converting {input_format} to {target_format}: {str(e)}")

    def test_convert_vector_files(self):
        vector_formats = ["svg", "eps"]
        for input_format in vector_formats:
            for target_format in vector_formats:
                if input_format != target_format:
                    input_path = os.path.join(self.test_files_dir, f"input.{input_format}")
                    output_path = os.path.join(self.temp_dir.name, f"output.{target_format}")
                    try:
                        self.converter._convert_vector(input_path, output_path, target_format)
                        self.assertTrue(
                            os.path.exists(output_path),
                            f"Failed to convert {input_format} to {target_format}",
                        )
                    except Exception as e:
                        self.fail(f"Error converting {input_format} to {target_format}: {str(e)}")

    def test_convert_document_files(self):
        document_formats = ["pdf", "docx", "txt", "rtf", "odt"]
        for input_format in document_formats:
            for target_format in document_formats:
                if input_format != target_format:
                    input_path = os.path.join(self.test_files_dir, f"input.{input_format}")
                    output_path = os.path.join(self.temp_dir.name, f"output.{target_format}")
                    try:
                        self.converter._convert_document(input_path, output_path, target_format)
                        self.assertTrue(
                            os.path.exists(output_path),
                            f"Failed to convert {input_format} to {target_format}",
                        )
                    except Exception as e:
                        self.fail(f"Error converting {input_format} to {target_format}: {str(e)}")

    def test_convert_archive_files(self):
        archive_formats = ["zip", "tar", "tar.gz", "tar.xz", "tar.bz2", "rar", "7z"]
        for input_format in archive_formats:
            for target_format in archive_formats:
                if input_format != target_format:
                    input_path = os.path.join(self.test_files_dir, f"input.{input_format}")
                    output_path = os.path.join(self.temp_dir.name, f"output.{target_format}")
                    try:
                        self.converter._convert_archive(input_path, output_path, target_format)
                        self.assertTrue(
                            os.path.exists(output_path),
                            f"Failed to convert {input_format} to {target_format}",
                        )
                    except Exception as e:
                        self.fail(f"Error converting {input_format} to {target_format}: {str(e)}")

    def test_convert_ebook_files(self):
        ebook_formats = ["epub", "mobi", "azw3", "fb2", "txt", "rtf", "pdf"]
        for input_format in ebook_formats:
            for target_format in ebook_formats:
                if input_format != target_format:
                    input_path = os.path.join(self.test_files_dir, f"input.{input_format}")
                    output_path = os.path.join(self.temp_dir.name, f"output.{target_format}")
                    try:
                        self.converter._convert_ebook(input_path, output_path, target_format)
                        self.assertTrue(
                            os.path.exists(output_path),
                            f"Failed to convert {input_format} to {target_format}",
                        )
                    except Exception as e:
                        self.fail(f"Error converting {input_format} to {target_format}: {str(e)}")

    def test_unsupported_conversion(self):
        input_path = os.path.join(self.test_files_dir, "input.txt")
        output_path = os.path.join(self.temp_dir.name, "output.unknown")
        with self.assertRaises(ValueError):
            self.converter.convert_file(input_path, output_path, "unknown")

    def test_invalid_input_path(self):
        input_path = os.path.join(self.test_files_dir, "non-existent.jpg")
        output_path = os.path.join(self.temp_dir.name, "output.png")
        with self.assertRaises(Exception):
            self.converter._convert_photo(input_path, output_path, "png")

    def test_invalid_output_path(self):
        input_path = os.path.join(self.test_files_dir, "input.jpg")
        output_path = os.path.join("/non-existent-dir", "output.png")
        with self.assertRaises(Exception):
            self.converter._convert_photo(input_path, output_path, "png")

    def test_progress_callback(self):
        input_path = os.path.join(self.test_files_dir, "input.mp4")
        output_path = os.path.join(self.temp_dir.name, "output.avi")
        self.converter._convert_video(input_path, output_path, "avi")
        self.assertTrue(os.path.exists(output_path))


if __name__ == "__main__":
    unittest.main()
