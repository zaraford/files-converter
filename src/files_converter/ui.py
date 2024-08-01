import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Pango, GLib
import gettext
import itertools
import multiprocessing
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from functools import partial
import magic
import mimetypes

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from files_converter.converter import FileConverter
except ImportError:
    from converter import FileConverter

_ = gettext.gettext  # _("Files Converter")


class FileCard(Gtk.ListBoxRow):
    def __init__(self, file_path, converter, parent_window):
        super().__init__()
        self.file_path = file_path
        self.converter = converter
        self.parent_window = parent_window
        self.current_format = self.converter.get_current_format(self.file_path)
        self.target_format = None
        self.build_ui()

    def build_ui(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.set_margin_top(6)
        card.set_margin_bottom(6)
        card.set_margin_start(12)
        card.set_margin_end(12)

        # Main content area
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        card.pack_start(content_box, True, True, 0)

        # Left side: Icon, filename, and metadata
        left_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        content_box.pack_start(left_box, True, True, 0)

        # File icon
        icon = Gtk.Image.new_from_icon_name(self.get_file_icon(), Gtk.IconSize.LARGE_TOOLBAR)
        left_box.pack_start(icon, False, False, 0)

        # File name and metadata
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        self.file_name_label = Gtk.Label(label=os.path.basename(self.file_path))
        self.file_name_label.set_halign(Gtk.Align.START)
        self.file_name_label.set_ellipsize(Pango.EllipsizeMode.END)
        info_box.pack_start(self.file_name_label, False, False, 0)

        self.metadata_label = Gtk.Label(label=self.get_file_metadata())
        self.metadata_label.set_halign(Gtk.Align.START)
        self.metadata_label.set_line_wrap(True)
        self.metadata_label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.metadata_label.set_max_width_chars(30)
        self.metadata_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.5, 0.5, 0.5, 1))
        info_box.pack_start(self.metadata_label, False, False, 0)

        left_box.pack_start(info_box, True, True, 0)

        # Right side: Conversion dropdown
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        content_box.pack_end(right_box, False, False, 0)

        to_label = Gtk.Label(label="Convert to:")
        to_label.set_halign(Gtk.Align.END)
        right_box.pack_start(to_label, False, False, 0)

        file_type = self.converter.get_file_type(self.file_path)
        target_formats = self.converter.get_target_formats(file_type)

        # Remove the current format from the target formats
        target_formats = [fmt for fmt in target_formats if fmt != self.current_format]

        self.to_combo = Gtk.ComboBoxText()
        self.to_combo.set_entry_text_column(0)
        for format in target_formats:
            self.to_combo.append_text(format)

        if target_formats:
            self.to_combo.set_active(0)
            self.target_format = target_formats[0]  # Initialize with the first format

        self.to_combo.connect("changed", self.on_format_changed)
        right_box.pack_start(self.to_combo, False, False, 0)

        # Action buttons
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        card.pack_start(action_box, False, False, 0)

        delete_button = Gtk.Button.new_from_icon_name("edit-delete-symbolic", Gtk.IconSize.BUTTON)
        delete_button.connect("clicked", self.on_delete_clicked)

        action_box.pack_end(delete_button, False, False, 0)

        self.add(card)

    def get_file_icon(self):
        mime_type, _ = mimetypes.guess_type(self.file_path)
        if mime_type:
            if mime_type.startswith("image/"):
                return "image-x-generic"
            elif mime_type.startswith("video/"):
                return "video-x-generic"
            elif mime_type.startswith("audio/"):
                return "audio-x-generic"
            elif mime_type.startswith("text/"):
                return "text-x-generic"
            elif "pdf" in mime_type:
                return "application-pdf"
            elif "msword" in mime_type or "officedocument" in mime_type:
                return "x-office-document"
        return "application-x-generic"

    def get_file_metadata(self):
        try:
            stat = os.stat(self.file_path)
            mime_type, _ = mimetypes.guess_type(self.file_path)

            size = self.format_size(stat.st_size)
            created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")

            metadata = f"Type: {mime_type or 'Unknown'}\n"
            metadata += f"Size: {size}\n"
            metadata += f"Created: {created}\n"

            return metadata
        except Exception as e:
            return f"Error retrieving metadata: {str(e)}"

    def format_size(self, size):
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0

    def on_delete_clicked(self, button):
        self.parent_window.remove_file(self)

    def on_format_changed(self, combo):
        self.target_format = combo.get_active_text()

    def get_file_path(self):
        return self.file_path

    def get_target_format(self):
        return self.target_format


class ConversionWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Files Converter")
        self.set_default_size(400, 500)
        self.converter = FileConverter()
        self.start_time = None
        self.current_progress = 0
        self.conversion_active = False
        self.file_queue = multiprocessing.Queue()
        self.processing_complete = threading.Event()
        self.batch_size = 100
        self.scan_start_time = None
        self.load_settings()
        self.build_ui()

    def build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        # Add menu bar
        menubar = Gtk.MenuBar()

        # File menu
        filemenu = Gtk.Menu()
        filem = Gtk.MenuItem("File")
        filem.set_submenu(filemenu)

        add_files = Gtk.MenuItem("Add files")
        add_files.connect("activate", self.on_select_files_clicked)
        filemenu.append(add_files)

        open_folder = Gtk.MenuItem("Open folder")
        open_folder.connect("activate", self.on_open_folder_clicked)
        filemenu.append(open_folder)

        # Settings menu
        settingsmenu = Gtk.Menu()
        settingsm = Gtk.MenuItem("Settings")
        settingsm.set_submenu(settingsmenu)

        settings_item = Gtk.MenuItem("Preferences")
        settings_item.connect("activate", self.open_settings)
        settingsmenu.append(settings_item)

        # Help menu
        helpmenu = Gtk.Menu()
        helpm = Gtk.MenuItem("Help")
        helpm.set_submenu(helpmenu)

        about_item = Gtk.MenuItem("About")
        about_item.connect("activate", self.show_about_dialog)
        helpmenu.append(about_item)

        report_bug = Gtk.MenuItem("Report a bug")
        report_bug.connect("activate", self.report_bug)
        helpmenu.append(report_bug)

        donate = Gtk.MenuItem("Support")
        donate.connect("activate", self.donate)
        helpmenu.append(donate)

        menubar.append(filem)
        menubar.append(settingsm)
        menubar.append(helpm)

        main_box.pack_start(menubar, False, False, 0)

        # Header
        header_label = Gtk.Label(label="Selected files:")
        header_label.set_halign(Gtk.Align.START)
        header_label.set_margin_left(20)
        header_label.set_margin_right(20)
        main_box.pack_start(header_label, False, False, 0)

        # File list
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_margin_left(20)
        scrolled_window.set_margin_right(20)

        self.file_list = Gtk.ListBox()
        self.file_list.set_selection_mode(Gtk.SelectionMode.NONE)

        scrolled_window.add(self.file_list)
        main_box.pack_start(scrolled_window, True, True, 0)

        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_margin_left(20)
        self.progress_bar.set_margin_right(20)
        main_box.pack_start(self.progress_bar, False, False, 0)
        self.progress_bar.set_show_text(True)

        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_right(20)
        separator.set_margin_left(20)
        main_box.pack_start(
            separator,
            False,
            False,
            5,
        )

        # Action buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        self.convert_button = Gtk.Button(label="Convert")
        self.convert_button.set_margin_right(5)
        self.convert_button.set_margin_bottom(20)
        self.convert_button.get_style_context().add_class("suggested-action")
        self.convert_button.connect("clicked", self.on_convert_clicked)

        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.set_margin_left(5)
        cancel_button.set_margin_right(20)
        cancel_button.set_margin_bottom(20)
        cancel_button.connect("clicked", self.on_cancel_clicked)

        button_box.pack_end(cancel_button, False, False, 0)
        button_box.pack_end(self.convert_button, False, False, 0)

        main_box.pack_end(button_box, False, False, 0)

        self.add(main_box)

    def on_select_files_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Please choose files", parent=self, action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        dialog.set_select_multiple(True)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            file_paths = dialog.get_filenames()
            for file_path in file_paths:
                file_card = FileCard(file_path, self.converter, self)
                self.file_list.add(file_card)
            self.file_list.show_all()

        dialog.destroy()

    def on_convert_clicked(self, widget):
        files_to_convert = self.file_list.get_children()
        if not files_to_convert:
            self.show_error_dialog("No files selected for conversion.")
            return

        output_dir = self.choose_output_directory()
        if not output_dir:
            return

        self.convert_button.set_sensitive(False)
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("0%")
        self.current_progress = 0
        self.conversion_active = True

        self.start_time = time.time()

        thread = threading.Thread(target=self.convert_files, args=(files_to_convert, output_dir))
        thread.daemon = True
        thread.start()

        GLib.timeout_add(1000, self.update_progress_bar)

    def convert_files(self, files, output_dir):
        total_files = len(files)
        for i, list_box_row in enumerate(files):
            file_card = list_box_row
            if isinstance(file_card, FileCard):
                input_path = file_card.get_file_path()
                target_format = file_card.get_target_format()
                if not target_format:
                    GLib.idle_add(
                        self.show_error_dialog,
                        f"No valid target format available for {os.path.basename(input_path)}",
                    )
                    continue

                output_path = os.path.join(
                    output_dir,
                    f"{os.path.splitext(os.path.basename(input_path))[0]}.{target_format}",
                )

                try:

                    def progress_callback(progress):
                        file_progress = (i + progress) / total_files
                        GLib.idle_add(self.set_progress, file_progress)

                    self.converter.convert_file(
                        input_path, output_path, target_format, progress_callback
                    )
                except Exception as e:
                    GLib.idle_add(
                        self.show_error_dialog,
                        f"Error converting {os.path.basename(input_path)}: {str(e)}",
                    )

            else:
                print(f"Unexpected item in file list: {type(file_card)}")

        GLib.idle_add(self.conversion_completed)

    def set_progress(self, progress):
        self.current_progress = progress

    def update_progress_bar(self):
        if not self.conversion_active:
            return False

        self.progress_bar.set_fraction(self.current_progress)

        elapsed_time = time.time() - self.start_time
        if self.current_progress > 0:
            estimated_total_time = elapsed_time / self.current_progress
            remaining_time = estimated_total_time - elapsed_time
            time_string = str(timedelta(seconds=int(remaining_time)))
            progress_text = f"{self.current_progress:.1%} (Est. {time_string} remaining)"
        else:
            progress_text = f"{self.current_progress:.1%}"

        self.progress_bar.set_text(progress_text)

        return True

    def conversion_completed(self):
        self.conversion_active = False
        self.convert_button.set_sensitive(True)
        self.progress_bar.set_fraction(1.0)
        self.progress_bar.set_text("Conversion completed")
        self.show_info_dialog("Conversion completed successfully!")

    def on_cancel_clicked(self, widget):
        self.destroy()

    def remove_file(self, file_card):
        self.file_list.remove(file_card)

    def choose_output_directory(self):
        dialog = Gtk.FileChooserDialog(
            title="Select Output Directory", parent=self, action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            output_dir = dialog.get_filename()
            dialog.destroy()
            return output_dir
        dialog.destroy()
        return None

    def show_error_dialog(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Error",
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def show_info_dialog(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Information",
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def on_open_folder_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Please choose a folder", parent=self, action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            folder_path = dialog.get_filename()
            self.add_folder(folder_path)

        dialog.destroy()

    def open_settings(self, widget):
        dialog = SettingsDialog(self)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            # Save settings
            lang = dialog.lang_combo.get_active_text()
            theme = dialog.theme_combo.get_active_text()
            output_dir = dialog.dir_combo.get_active_text()
            # Save these settings to a file or GSettings
            self.save_settings(lang, theme, output_dir)

        dialog.destroy()

    def show_about_dialog(self, widget):
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_transient_for(self)
        about_dialog.set_modal(True)

        about_dialog.set_program_name("Files Converter")
        about_dialog.set_version("0.1.0")
        about_dialog.set_copyright("© 2024 Vladyslav Lodzhuk")
        about_dialog.set_comments("A file conversion utility with context menu integration")
        about_dialog.set_website("https://github.com/zaraford/files-converter")
        about_dialog.set_website_label("GitHub Repository")
        about_dialog.set_license_type(Gtk.License.MIT_X11)

        about_dialog.run()
        about_dialog.destroy()

    def report_bug(self, widget):
        Gtk.show_uri_on_window(
            self, "https://github.com/zaraford/files-converter/issues", Gdk.CURRENT_TIME
        )

    def donate(self, widget):
        Gtk.show_uri_on_window(self, "https://ko-fi.com/zaraford", Gdk.CURRENT_TIME)

    def save_settings(self, lang, theme, output_dir):
        # Implement saving settings to a file or GSettings
        pass

    def load_settings(self):
        # Implement loading settings from a file or GSettings
        pass

    def add_file_or_folder(self, path):
        if os.path.isfile(path):
            if self.is_supported_file(path, self.get_supported_extensions()):
                self.add_file(path)
        elif os.path.isdir(path):
            self.add_folder(path)

    def add_folder(self, folder_path):
        self.show_progress_dialog("Processing folder", "Scanning for supported files...")

        # Record the start time
        self.scan_start_time = time.time()

        # Start the file processing in a separate thread
        threading.Thread(target=self.process_folder, args=(folder_path,), daemon=True).start()

        # Start the UI update process
        GLib.timeout_add(100, self.update_ui_from_queue)

    def process_folder(self, folder_path):
        supported_extensions = self.get_supported_extensions()
        with multiprocessing.Pool() as pool:
            for root, dirs, files in os.walk(folder_path):
                file_paths = [os.path.join(root, file) for file in files]
                chunk_size = max(1, len(file_paths) // (multiprocessing.cpu_count() * 4))
                for supported_file in pool.imap_unordered(
                    partial(self.is_supported_file, supported_extensions=supported_extensions),
                    file_paths,
                    chunksize=chunk_size,
                ):
                    if supported_file:
                        self.file_queue.put(supported_file)

        self.processing_complete.set()

    @staticmethod
    def is_supported_file(file_path, supported_extensions):
        _, ext = os.path.splitext(file_path)
        if ext.lower() in supported_extensions:
            return file_path
        return None

    def get_supported_extensions(self):
        supported_extensions = set()
        for formats in self.converter.supported_formats.values():
            supported_extensions.update(f".{fmt.lower()}" for fmt in formats)
        return supported_extensions

    def update_ui_from_queue(self):
        files_processed = 0
        start_time = time.time()
        while not self.file_queue.empty() and files_processed < self.batch_size:
            file_path = self.file_queue.get()
            self.add_file(file_path)
            files_processed += 1

            # Check if we've spent too much time adding files
            if time.time() - start_time > 0.1:  # 100ms
                break

        if files_processed > 0:
            self.file_list.show_all()

        if self.processing_complete.is_set() and self.file_queue.empty():
            self.hide_progress_dialog()
            elapsed_time = time.time() - self.scan_start_time
            formatted_time = self.format_time(elapsed_time)
            total_files = len(self.file_list.get_children())

            if total_files > 0:
                message = (
                    f"Added {total_files} supported files.\n" f"Scan completed in {formatted_time}."
                )
                self.show_info_dialog(message)
            else:
                self.show_info_dialog("No supported files found in the selected folder.")

            # Reset the start time
            self.scan_start_time = None
            return False

        return True

    def format_time(self, seconds):
        if seconds < 60:
            return f"{seconds:.2f} seconds"
        else:
            minutes, seconds = divmod(seconds, 60)
            return f"{int(minutes)} minutes and {seconds:.2f} seconds"

    def add_file(self, file_path):
        file_card = FileCard(file_path, self.converter, self)
        self.file_list.add(file_card)
        self.file_list.show_all()

    def show_progress_dialog(self, title, message):
        self.progress_dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.NONE,
            text=title,
        )
        self.progress_dialog.format_secondary_text(message)
        self.progress_dialog.show_all()

    def hide_progress_dialog(self):
        if hasattr(self, "progress_dialog"):
            self.progress_dialog.destroy()
            del self.progress_dialog


class SettingsDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="Preferences", transient_for=parent, flags=0)
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK
        )

        self.set_default_size(300, 200)

        box = self.get_content_area()

        # Language setting
        lang_label = Gtk.Label("Language:")
        self.lang_combo = Gtk.ComboBoxText()
        self.lang_combo.append_text("English")
        self.lang_combo.append_text("Українська")
        self.lang_combo.set_active(0)

        # Theme setting
        theme_label = Gtk.Label("Theme:")
        self.theme_combo = Gtk.ComboBoxText()
        self.theme_combo.append_text("System default")
        self.theme_combo.append_text("Light")
        self.theme_combo.append_text("Dark")
        self.theme_combo.set_active(0)

        # Output directory setting
        dir_label = Gtk.Label("Default output directory:")
        self.dir_combo = Gtk.ComboBoxText()
        self.dir_combo.append_text("Same as input")
        self.dir_combo.append_text("Choose directory")
        self.dir_combo.append_text("Ask each time")
        self.dir_combo.set_active(0)

        box.add(lang_label)
        box.add(self.lang_combo)
        box.add(theme_label)
        box.add(self.theme_combo)
        box.add(dir_label)
        box.add(self.dir_combo)

        self.show_all()


def main():
    win = ConversionWindow()
    win.connect("destroy", Gtk.main_quit)
    # Add files from command-line arguments
    for path in sys.argv[1:]:
        GLib.idle_add(win.add_file_or_folder, path)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
