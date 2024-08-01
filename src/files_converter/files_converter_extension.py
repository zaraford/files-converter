import gi

gi.require_version("Nautilus", "3.0")
import os
import subprocess

from gi.repository import GObject, Nautilus

from files_converter.converter import FileConverter


class FilesConverterExtension(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        self.converter = FileConverter()

    def is_supported_file(self, file):
        if file.is_directory():
            return True
        file_path = file.get_location().get_path()
        file_type = self.converter.get_file_type(file_path)
        return file_type is not None

    def get_file_items(self, window, files):
        # Check if any of the selected files are supported or if there are folders
        supported_files = [
            file for file in files if self.is_supported_file(file) or file.is_directory()
        ]

        if not supported_files:
            return []

        items = []

        # Add "Convert" option for files
        file_items = [file for file in supported_files if not file.is_directory()]
        if file_items:
            convert_item = Nautilus.MenuItem(
                name="FilesConverterExtension::Convert",
                label="Convert",
                tip="Convert selected files",
                icon="",
            )
            convert_item.connect("activate", self.on_convert_clicked, file_items)
            items.append(convert_item)

        # Add "Open in Files Converter" option for folders
        folder_items = [file for file in supported_files if file.is_directory()]
        if folder_items:
            open_folder_item = Nautilus.MenuItem(
                name="FilesConverterExtension::OpenFolder",
                label="Open in Files Converter",
                tip="Open selected folders in Files Converter",
                icon="",
            )
            open_folder_item.connect("activate", self.on_open_folder_clicked, folder_items)
            items.append(open_folder_item)

        return items

    def on_convert_clicked(self, item, files):
        file_paths = [file.get_location().get_path() for file in files]
        subprocess.Popen(["files-converter"] + file_paths)

    def on_open_folder_clicked(self, item, folders):
        folder_paths = [folder.get_location().get_path() for folder in folders]
        subprocess.Popen(["files-converter"] + folder_paths)
