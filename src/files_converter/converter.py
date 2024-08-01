import os
import re
import shutil
import subprocess
import tarfile
import zipfile

import docx
import ffmpeg
import PyPDF2
from PIL import Image


class FileConverter:
    def __init__(self):
        self.supported_formats = {
            "photos": ["jpg", "png", "gif", "bmp", "tiff", "webp"],
            "videos": ["mp4", "avi", "mov", "mkv", "webm"],
            "vectors": ["svg", "eps", "ai"],
            "audio": ["mp3", "wav", "ogg", "flac", "aac"],
            "documents": ["pdf", "docx", "txt", "rtf", "odt"],
            "archives": ["zip", "tar", "gz", "rar", "7z"],
            "ebooks": ["epub", "mobi", "azw3", "fb2", "lit", "txt", "rtf", "pdf"],
        }

    def get_file_type(self, file_path):
        extension = os.path.splitext(file_path)[1][1:].lower()
        for file_type, formats in self.supported_formats.items():
            if extension in formats:
                return file_type
        return None

    def get_target_formats(self, file_type):
        return self.supported_formats.get(file_type, [])

    def get_current_format(self, file_path):
        return os.path.splitext(file_path)[1][1:].lower()

    def convert_file(self, input_path, output_path, target_format, progress_callback=None):
        self.progress_callback = progress_callback
        file_type = self.get_file_type(input_path)

        if file_type == "photos":
            self._convert_photo(input_path, output_path, target_format)
        elif file_type == "videos":
            self._convert_video(input_path, output_path, target_format)
        elif file_type == "vectors":
            self._convert_vector(input_path, output_path, target_format)
        elif file_type == "audio":
            self._convert_audio(input_path, output_path, target_format)
        elif file_type == "documents":
            self._convert_document(input_path, output_path, target_format)
        elif file_type == "archives":
            self._convert_archive(input_path, output_path, target_format)
        elif file_type == "ebooks":
            self._convert_ebook(input_path, output_path, target_format)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def _convert_photo(self, input_path, output_path, target_format):
        with Image.open(input_path) as img:
            if target_format == "jpg":
                target_format = "jpeg"
                img = img.convert("RGB")
            img.save(output_path, format=target_format)

    def _convert_video(self, input_path, output_path, target_format):
        try:
            # Get video duration
            probe = ffmpeg.probe(input_path)
            duration = float(probe["streams"][0]["duration"])

            # Set up the conversion
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.output(stream, output_path, format=target_format)

            # Run the conversion
            process = ffmpeg.run_async(stream, pipe_stderr=True)

            # Monitor the conversion progress
            pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.\d{2}")
            while True:
                line = process.stderr.readline().decode("utf8")
                if not line:
                    break
                match = pattern.search(line)
                if match:
                    hours, minutes, seconds = map(int, match.groups())
                    time_processed = hours * 3600 + minutes * 60 + seconds
                    progress = time_processed / duration
                    if self.progress_callback:
                        self.progress_callback(progress)

            # Ensure the process is complete
            process.wait()

            if process.returncode != 0:
                raise Exception(f"ffmpeg process failed with return code: {process.returncode}")

        except ffmpeg.Error as e:
            print("stdout:", e.stdout.decode("utf8"))
            print("stderr:", e.stderr.decode("utf8"))
            raise
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            raise

    def _convert_vector(self, input_path, output_path, target_format):
        if shutil.which("inkscape"):
            subprocess.run(["inkscape", input_path, f"--export-filename={output_path}"])
        else:
            raise RuntimeError("Inkscape is required for vector conversions but is not installed.")

    def _convert_audio(self, input_path, output_path, target_format):
        (
            ffmpeg.input(input_path)
            .output(output_path, format=target_format)
            .overwrite_output()
            .run()
        )

    def _convert_document(self, input_path, output_path, target_format):
        if target_format == "pdf":
            if input_path.endswith(".docx"):
                doc = docx.Document(input_path)
                doc.save(output_path)
            elif input_path.endswith(".txt"):
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas

                c = canvas.Canvas(output_path, pagesize=letter)
                with open(input_path, "r") as txt_file:
                    text = txt_file.read()
                    c.drawString(72, 800, text)
                c.save()
        elif target_format == "txt":
            if input_path.endswith(".pdf"):
                with open(input_path, "rb") as pdf_file:
                    reader = PyPDF2.PdfReader(pdf_file)
                    with open(output_path, "w") as txt_file:
                        for page in reader.pages:
                            txt_file.write(page.extract_text())
            elif input_path.endswith(".docx"):
                doc = docx.Document(input_path)
                with open(output_path, "w") as txt_file:
                    for para in doc.paragraphs:
                        txt_file.write(para.text + "\n")
        else:
            raise ValueError(
                f"Unsupported document conversion: {os.path.splitext(input_path)[1]} to {target_format}"
            )

    def _convert_archive(self, input_path, output_path, target_format):
        temp_dir = os.path.join(os.path.dirname(output_path), "temp_extract")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            # Extract the input archive
            if input_path.endswith((".tar", ".gz", ".bz2")):
                with tarfile.open(input_path, "r:*") as tar:
                    tar.extractall(temp_dir)
            elif input_path.endswith(".zip"):
                with zipfile.ZipFile(input_path, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)
            elif input_path.endswith(".rar"):
                subprocess.run(["unrar", "x", input_path, temp_dir])
            elif input_path.endswith(".7z"):
                subprocess.run(["7z", "x", input_path, f"-o{temp_dir}"])

            # Create the output archive
            if target_format == "zip":
                shutil.make_archive(output_path[:-4], "zip", temp_dir)
            elif target_format in ["tar", "gz"]:
                shutil.make_archive(output_path[:-4], "gztar", temp_dir)
            elif target_format == "rar":
                subprocess.run(["rar", "a", output_path, temp_dir])
            elif target_format == "7z":
                subprocess.run(["7z", "a", output_path, f"{temp_dir}/*"])
            else:
                raise ValueError(f"Unsupported archive format: {target_format}")

        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _convert_ebook(self, input_path, output_path, target_format):
        try:
            subprocess.run(["ebook-convert", input_path, output_path], check=True)
        except subprocess.CalledProcessError:
            raise RuntimeError(f"Failed to convert ebook from {input_path} to {output_path}")

    def batch_convert(self, file_list, output_dir, target_format):
        for input_path in file_list:
            file_name = os.path.basename(input_path)
            name, _ = os.path.splitext(file_name)
            output_path = os.path.join(output_dir, f"{name}.{target_format}")
            self.convert_file(input_path, output_path, target_format)
