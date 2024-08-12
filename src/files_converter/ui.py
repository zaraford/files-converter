import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Pango, GLib, GdkPixbuf, GObject
import gettext
import locale
import multiprocessing
import json
import os
from pathlib import Path
import sys
import threading
import time
from datetime import datetime, timedelta
from functools import partial
import mimetypes

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from src.files_converter.converter import FileConverter
except ImportError:
    from converter import FileConverter


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
        self.file_name_label.set_tooltip_text(os.path.basename(self.file_path))
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

        self.to_label = Gtk.Label(label=_("Convert to:"))
        self.to_label.set_halign(Gtk.Align.END)
        right_box.pack_start(self.to_label, False, False, 0)

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
        action_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
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
            mime_type, a = mimetypes.guess_type(self.file_path)

            size = self.format_size(stat.st_size)
            created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")

            metadata = _("Type: {mime_type}\n").format(mime_type=mime_type or "Unknown")
            metadata += _("Size: {size}\n").format(size=size)
            metadata += _("Created: {created}\n").format(created=created)

            return metadata
        except Exception as e:
            return _("Error retrieving metadata: {}").format(str(e))

    def format_size(self, size):
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0

    def on_delete_clicked(self, button):
        self.parent_window.remove_file(self)
        self.parent_window.update_clear_all_button()

    def on_format_changed(self, combo):
        self.target_format = combo.get_active_text()

    def get_file_path(self):
        return self.file_path

    def get_target_format(self):
        return self.target_format

    def update_text(self):
        self.file_name_label.set_text(os.path.basename(self.file_path))
        self.metadata_label.set_text(self.get_file_metadata())
        self.to_label.set_label(_("Convert to:"))


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
        self.clear_all_button = None
        self.added_files = set()
        self.conversion_weights = {
            "photos": 1,
            "videos": 5,
            "vectors": 2,
            "audio": 1.5,
            "documents": 1,
            "archives": 3,
            "ebooks": 1.2,
        }
        self.total_weighted_size = 0
        self.converted_weighted_size = 0
        self.settings = self.load_settings()
        self.build_ui()
        self.apply_settings()

    def build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        # Add menu bar
        menubar = Gtk.MenuBar()

        # File menu
        filemenu = Gtk.Menu()
        self.filem = Gtk.MenuItem(label=_("File"))
        self.filem.set_submenu(filemenu)

        self.add_files = Gtk.MenuItem(label=_("Add files"))
        self.add_files.connect("activate", self.on_select_files_clicked)
        filemenu.append(self.add_files)

        self.open_folder = Gtk.MenuItem(label=_("Open folder"))
        self.open_folder.connect("activate", self.on_open_folder_clicked)
        filemenu.append(self.open_folder)

        # Settings menu
        settingsmenu = Gtk.Menu()
        self.settingsm = Gtk.MenuItem(label=_("Settings"))
        self.settingsm.set_submenu(settingsmenu)

        self.settings_item = Gtk.MenuItem(label=_("Preferences"))
        self.settings_item.connect("activate", self.open_settings)
        settingsmenu.append(self.settings_item)

        # Help menu
        helpmenu = Gtk.Menu()
        self.helpm = Gtk.MenuItem(label=_("Help"))
        self.helpm.set_submenu(helpmenu)

        self.about_item = Gtk.MenuItem(label=_("About"))
        self.about_item.connect("activate", self.open_about_dialog)
        helpmenu.append(self.about_item)

        self.report_bug = Gtk.MenuItem(label=_("Report a bug"))
        self.report_bug.connect("activate", self.open_report_bug)
        helpmenu.append(self.report_bug)

        self.donate = Gtk.MenuItem(label=_("Support"))
        self.donate.connect("activate", self.open_donate)
        helpmenu.append(self.donate)

        menubar.append(self.filem)
        menubar.append(self.settingsm)
        menubar.append(self.helpm)

        main_box.pack_start(menubar, False, False, 0)

        # Header
        self.header_label = Gtk.Label(label=_("Selected files:"))
        self.header_label.set_halign(Gtk.Align.START)
        self.header_label.set_margin_left(20)
        self.header_label.set_margin_right(20)
        main_box.pack_start(self.header_label, False, False, 0)

        # File list
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_margin_left(20)
        scrolled_window.set_margin_right(20)

        self.file_list = Gtk.ListBox()
        self.file_list.set_selection_mode(Gtk.SelectionMode.NONE)

        scrolled_window.add(self.file_list)

        # Add a container for the file list and clear all button
        file_list_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.pack_start(file_list_container, True, True, 0)

        # Move the existing file list into this container
        file_list_container.pack_start(scrolled_window, True, True, 0)

        # Create the clear all button (initially hidden)
        self.clear_all_button = Gtk.Button(label=_("Clear All"))
        self.clear_all_button.set_margin_left(20)
        self.clear_all_button.set_margin_right(20)
        self.clear_all_button.connect("clicked", self.on_clear_all_clicked)
        self.clear_all_button.set_no_show_all(True)  # Don't show by default
        file_list_container.pack_start(self.clear_all_button, False, False, 0)

        # Separator
        self.separator_clear = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.separator_clear.set_margin_right(20)
        self.separator_clear.set_margin_left(20)
        self.separator_clear.set_no_show_all(True)
        main_box.pack_start(
            self.separator_clear,
            False,
            False,
            5,
        )

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

        self.convert_button = Gtk.Button(label=_("Convert"))
        self.convert_button.set_margin_right(5)
        self.convert_button.set_margin_bottom(20)
        self.convert_button.get_style_context().add_class("suggested-action")
        self.convert_button.connect("clicked", self.on_convert_clicked)

        self.cancel_button = Gtk.Button(label=_("Cancel"))
        self.cancel_button.set_margin_left(5)
        self.cancel_button.set_margin_right(20)
        self.cancel_button.set_margin_bottom(20)
        self.cancel_button.connect("clicked", self.on_cancel_clicked)

        button_box.pack_end(self.cancel_button, False, False, 0)
        button_box.pack_end(self.convert_button, False, False, 0)

        main_box.pack_end(button_box, False, False, 0)

        self.add(main_box)

    def on_select_files_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title=_("Please choose files"), parent=self, action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        dialog.set_select_multiple(True)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            file_paths = dialog.get_filenames()
            for file_path in file_paths:
                if self.is_supported_file(file_path, self.get_supported_extensions()):
                    self.add_file(file_path)

        dialog.destroy()

    def on_convert_clicked(self, widget):
        files_to_convert = self.file_list.get_children()
        if not files_to_convert:
            self.show_error_dialog(_("No files selected for conversion."))
            return

        if self.default_output_dir == "ask":
            output_dir = self.choose_output_directory()
            if not output_dir:
                return
        elif self.default_output_dir == "custom":
            if self.custom_output_dir:
                output_dir = self.custom_output_dir
            else:
                self.show_error_dialog(
                    _(
                        "No custom directory has been selected for conversion. Please select a directory to proceed."
                    )
                )
                return
        else:  # "Same as input"
            output_dir = None  # Will be set per file in the conversion process

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
        self.total_weighted_size = self.calculate_total_weighted_size(files)
        self.converted_weighted_size = 0
        successfully_converted = []

        for list_box_row in files:
            file_card = list_box_row
            if isinstance(file_card, FileCard):
                input_path = file_card.get_file_path()
                target_format = file_card.get_target_format()
                if not target_format:
                    GLib.idle_add(
                        self.show_error_dialog,
                        _("No valid target format available for {}").format(
                            os.path.basename(input_path)
                        ),
                    )
                    continue

                if output_dir is None:  # "Same as input"
                    output_dir = os.path.dirname(input_path)

                output_path = os.path.join(
                    output_dir,
                    f"{os.path.splitext(os.path.basename(input_path))[0]}.{target_format}",
                )

                try:
                    file_type = self.converter.get_file_type(input_path)
                    file_size = os.path.getsize(input_path)
                    file_weight = self.conversion_weights.get(file_type, 1)
                    weighted_size = file_size * file_weight

                    file_progress = 0  # Track progress for this specific file

                    def progress_callback(progress):
                        nonlocal file_progress
                        new_file_progress = progress * weighted_size
                        progress_diff = new_file_progress - file_progress
                        file_progress = new_file_progress
                        self.converted_weighted_size += progress_diff
                        overall_progress = min(
                            self.converted_weighted_size / self.total_weighted_size, 1.0
                        )
                        GLib.idle_add(self.set_progress, overall_progress)

                    self.converter.convert_file(
                        input_path, output_path, target_format, progress_callback
                    )
                    successfully_converted.append(file_card)

                    # Ensure we've accounted for the full file size after conversion
                    if file_progress < weighted_size:
                        remaining_progress = weighted_size - file_progress
                        self.converted_weighted_size += remaining_progress
                        overall_progress = min(
                            self.converted_weighted_size / self.total_weighted_size, 1.0
                        )
                        GLib.idle_add(self.set_progress, overall_progress)

                except Exception as e:
                    GLib.idle_add(
                        self.show_error_dialog,
                        _("Error converting {}: {}").format(os.path.basename(input_path), str(e)),
                    )

            else:
                print(_("Unexpected item in file list: {}").format(type(file_card)))

        if self.autoremove_converted:
            GLib.idle_add(self.remove_converted_files, successfully_converted)

        GLib.idle_add(self.conversion_completed)

    def calculate_total_weighted_size(self, files):
        total = 0
        for list_box_row in files:
            if isinstance(list_box_row, FileCard):
                file_path = list_box_row.get_file_path()
                file_type = self.converter.get_file_type(file_path)
                file_size = os.path.getsize(file_path)
                weight = self.conversion_weights.get(file_type, 1)
                total += file_size * weight
        return total

    def set_progress(self, progress):
        self.current_progress = progress
        self.progress_bar.set_fraction(progress)
        self.update_progress_bar()

    def update_progress_bar(self):
        if not self.conversion_active:
            return False

        elapsed_time = time.time() - self.start_time
        if self.current_progress > 0:
            estimated_total_time = elapsed_time / self.current_progress
            remaining_time = estimated_total_time - elapsed_time
            time_string = str(timedelta(seconds=int(remaining_time)))
            progress_text = f"{self.current_progress:.1%} " + _("(Est. {} remaining)").format(
                time_string
            )
        else:
            progress_text = f"{self.current_progress:.1%}"

        self.progress_bar.set_text(progress_text)

        return True

    def conversion_completed(self):
        self.conversion_active = False
        self.convert_button.set_sensitive(True)
        self.progress_bar.set_fraction(1.0)
        self.progress_bar.set_text(_("Conversion completed"))
        self.show_info_dialog(_("Conversion completed successfully!"))

        # Schedule the progress bar reset after 5 seconds
        GLib.timeout_add_seconds(5, self.reset_progress_bar)

    def reset_progress_bar(self):
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("0%")
        # Return False to ensure this function is only called once
        return False

    def on_cancel_clicked(self, widget):
        self.destroy()

    def remove_file(self, file_card):
        self.file_list.remove(file_card)
        self.added_files.remove(file_card.get_file_path())
        self.update_clear_all_button()

    def update_clear_all_button(self):
        file_count = len(self.file_list.get_children())
        if file_count > 5:
            self.clear_all_button.show()
            self.separator_clear.show()
        else:
            self.clear_all_button.hide()
            self.separator_clear.hide()

    def on_clear_all_clicked(self, button):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=_("Clear all files?"),
        )
        dialog.format_secondary_text(_("Are you sure you want to remove all files from the list?"))
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            self.clear_all_files()
        dialog.destroy()

    def clear_all_files(self):
        for child in self.file_list.get_children():
            self.file_list.remove(child)
        self.added_files.clear()
        self.update_clear_all_button()

    def choose_output_directory(self):
        dialog = Gtk.FileChooserDialog(
            title=_("Select Output Directory"),
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
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
            text=_("Error"),
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def show_info_dialog(self, message):
        if self.notifications_enabled:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=_("Information"),
            )
            dialog.format_secondary_text(message)
            dialog.run()
            dialog.destroy()

    def on_open_folder_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title=_("Please choose a folder"),
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            folder_path = dialog.get_filename()
            self.add_folder(folder_path)
            self.update_clear_all_button()

        dialog.destroy()

    def open_about_dialog(self, widget):
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_transient_for(self)
        about_dialog.set_modal(True)

        about_dialog.set_program_name("Files Converter")
        about_dialog.set_version("0.1.0")
        about_dialog.set_copyright("© 2024 Vladyslav Lodzhuk")
        about_dialog.set_comments(_("A file conversion utility with context menu integration"))
        about_dialog.set_website("https://github.com/zaraford/files-converter")
        about_dialog.set_website_label(_("GitHub Repository"))
        about_dialog.set_license_type(Gtk.License.MIT_X11)

        # Add the logo
        icon_path = "/usr/share/icons/hicolor/96x96/apps/files-converter.png"
        if os.path.exists(icon_path):
            logo = GdkPixbuf.Pixbuf.new_from_file(icon_path)
            about_dialog.set_logo(logo)
        else:
            print(_("Warning: Icon file not found at {icon_path}").format(icon_path=icon_path))

        about_dialog.run()
        about_dialog.destroy()

    def open_report_bug(self, widget):
        Gtk.show_uri_on_window(
            self, "https://github.com/zaraford/files-converter/issues", Gdk.CURRENT_TIME
        )

    def open_donate(self, widget):
        Gtk.show_uri_on_window(self, "https://ko-fi.com/zaraford", Gdk.CURRENT_TIME)

    def get_settings_path(self):
        config_dir = Path.home() / ".config" / "files-converter"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "settings.json"

    def open_settings(self, widget):
        dialog = SettingsDialog(self, self.settings)
        dialog.run()
        dialog.destroy()

    def save_settings(self):
        settings_path = self.get_settings_path()
        with open(settings_path, "w") as f:
            json.dump(self.settings, f, indent=2)

    def load_settings(self):
        settings_path = self.get_settings_path()
        language = locale.getdefaultlocale()[0][:2]
        lang_code = (
            language if language in ["en", "cs", "de", "es", "fr", "it", "pl", "uk"] else "en"
        )
        self.load_translations(lang_code)
        default_settings = {
            "language": lang_code,
            "theme": "system",
            "output_directory": "same",
            "custom_directory": "",
            "notifications_enabled": True,
            "autoremove_converted": False,
        }

        if settings_path.exists():
            try:
                with open(settings_path, "r") as f:
                    loaded_settings = json.load(f)
                    # Update default settings with loaded settings
                    default_settings.update(loaded_settings)
            except json.JSONDecodeError:
                print(_("Error reading settings file. Using default settings."))
        else:
            # Save default settings if file doesn't exist
            with open(settings_path, "w") as f:
                json.dump(default_settings, f, indent=2)

        return default_settings

    def apply_settings(self):
        # Apply language
        lang_code = self.settings["language"]
        self.load_translations(lang_code)
        self.update_interface_text()

        # Apply theme
        self.set_theme(self.settings["theme"])

        # Apply output directory setting
        self.default_output_dir = self.settings["output_directory"]
        if self.default_output_dir == "custom":
            self.custom_output_dir = self.settings["custom_directory"]
        else:
            self.custom_output_dir = None

        # Apply notifications setting
        self.notifications_enabled = self.settings["notifications_enabled"]

        # Apply autoremove setting
        self.autoremove_converted = self.settings["autoremove_converted"]

    def load_translations(self, lang_code):
        try:
            lang = gettext.translation(
                "files-converter", localedir="/usr/share/locale", languages=[lang_code]
            )
            lang.install()
            global _
            _ = lang.gettext
        except FileNotFoundError:
            print(f"No translation found for {lang_code}.")

    def update_interface_text(self):
        # Update menu items
        self.filem.set_label(_("File"))
        self.settingsm.set_label(_("Settings"))
        self.helpm.set_label(_("Help"))
        self.add_files.set_label(_("Add files"))
        self.open_folder.set_label(_("Open folder"))
        self.settings_item.set_label(_("Preferences"))
        self.about_item.set_label(_("About"))
        self.report_bug.set_label(_("Report a bug"))
        self.donate.set_label(_("Support"))

        # Update header label
        self.header_label.set_label(_("Selected files:"))

        # Update clear all button
        if self.clear_all_button:
            self.clear_all_button.set_label(_("Clear All"))

        # Update convert button
        self.convert_button.set_label(_("Convert"))
        self.cancel_button.set_label(_("Cancel"))

        # Update file cards
        for child in self.file_list.get_children():
            if isinstance(child, FileCard):
                child.update_text()

    def set_theme(self, theme):
        settings = Gtk.Settings.get_default()
        if theme == "system":
            # Reset to system default
            settings.reset_property("gtk-application-prefer-dark-theme")
        elif theme == "light":
            settings.set_property("gtk-application-prefer-dark-theme", False)
        elif theme == "dark":
            settings.set_property("gtk-application-prefer-dark-theme", True)

        # Force theme update
        self.queue_draw()
        for widget in self.get_children():
            widget.queue_draw()

    def add_file_or_folder(self, path):
        if os.path.isfile(path):
            if self.is_supported_file(path, self.get_supported_extensions()):
                self.add_file(path)
        elif os.path.isdir(path):
            self.add_folder(path)

    def add_folder(self, folder_path):
        self.show_progress_dialog(_("Processing folder"), _("Scanning for supported files..."))

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
                    if supported_file and supported_file not in self.added_files:
                        self.file_queue.put(supported_file)

        self.processing_complete.set()

    @staticmethod
    def is_supported_file(file_path, supported_extensions):
        ext = "." + ".".join(os.path.basename(file_path).split(os.extsep)[1:])
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
            if file_path not in self.added_files:
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
                message = _(
                    "Added {total_files} supported files.\nScan completed in {formatted_time}."
                ).format(total_files=total_files, formatted_time=formatted_time)
                self.show_info_dialog(message)
            else:
                self.show_info_dialog(_("No supported files found in the selected folder."))

            # Reset the start time
            self.scan_start_time = None
            return False

        return True

    def format_time(self, seconds):
        if seconds < 60:
            return f"{seconds:.2f} " + _("seconds")
        else:
            minutes, seconds = divmod(seconds, 60)
            return _("{} minutes and").format(int(minutes)) + f" {seconds:.2f} " + _("seconds")

    def add_file(self, file_path):
        if file_path not in self.added_files:
            file_card = FileCard(file_path, self.converter, self)
            self.file_list.add(file_card)
            self.update_clear_all_button()
            self.file_list.show_all()
            self.added_files.add(file_path)

    def show_progress_dialog(self, title, message):
        if self.notifications_enabled:
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

    def remove_converted_files(self, files_to_remove):
        for file_card in files_to_remove:
            self.file_list.remove(file_card)
            self.added_files.remove(file_card.get_file_path())
        self.update_clear_all_button()


class SettingsDialog(Gtk.Dialog):
    __gsignals__ = {"language-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,))}

    def __init__(self, parent, current_settings):
        super().__init__(title=_("Preferences"), transient_for=parent, flags=0)
        self.set_default_size(400, 250)
        self.set_border_width(10)

        self.parent = parent
        self.current_settings = current_settings

        box = self.get_content_area()
        box.set_spacing(10)

        # Create a grid to organize the settings
        self.grid = Gtk.Grid()
        self.grid.set_column_spacing(20)
        self.grid.set_row_spacing(10)
        box.pack_start(self.grid, True, True, 0)

        # Language setting
        self.lang_label = Gtk.Label(label=_("Language:"))
        self.lang_label.set_halign(Gtk.Align.START)
        self.lang_combo = Gtk.ComboBoxText()
        self.lang_combo.set_hexpand(True)
        languages = [
            ("en", "English"),
            ("cs", "Čeština"),
            ("de", "Deutsch"),
            ("es", "Español"),
            ("fr", "Français"),
            ("it", "Italiano"),
            ("pl", "Polski"),
            ("uk", "Українська"),
        ]
        for lang_code, lang_name in languages:
            self.lang_combo.append(lang_code, lang_name)
        self.lang_combo.set_active_id(current_settings["language"])
        self.lang_combo.connect("changed", self.on_setting_changed)

        # Theme setting
        self.theme_label = Gtk.Label(label=_("Theme:"))
        self.theme_label.set_halign(Gtk.Align.START)
        self.theme_combo = Gtk.ComboBoxText()
        self.theme_combo.set_hexpand(True)
        themes = [("system", _("System default")), ("light", _("Light")), ("dark", _("Dark"))]
        for theme_id, theme_name in themes:
            self.theme_combo.append(theme_id, theme_name)
        self.theme_combo.set_active_id(current_settings["theme"])
        self.theme_combo.connect("changed", self.on_setting_changed)

        # Create a box for the theme combo and icon
        theme_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        theme_box.pack_start(self.theme_combo, True, True, 0)

        # Add exclamation mark icon
        self.theme_icon = Gtk.Image.new_from_icon_name("dialog-info-symbolic", Gtk.IconSize.BUTTON)
        self.theme_icon.set_tooltip_text("")
        theme_box.pack_start(self.theme_icon, False, False, 0)

        # Output directory setting
        self.dir_label = Gtk.Label(label=_("Default output directory:"))
        self.dir_label.set_halign(Gtk.Align.START)
        self.dir_combo = Gtk.ComboBoxText()
        self.dir_combo.set_hexpand(True)
        dir_options = [
            ("same", _("Same as input")),
            ("custom", _("Choose directory")),
            ("ask", _("Ask each time")),
        ]
        for dir_id, dir_name in dir_options:
            self.dir_combo.append(dir_id, dir_name)
        self.dir_combo.set_active_id(current_settings["output_directory"])
        self.dir_combo.connect("changed", self.on_dir_combo_changed)

        # Custom directory options
        self.custom_dir_button = Gtk.Button(label=_("Choose custom directory"))
        self.custom_dir_button.connect("clicked", self.on_custom_dir_clicked)
        self.custom_dir = current_settings["custom_directory"]
        self.custom_dir_label = Gtk.Label(label=self.custom_dir or _("Not selected"))
        self.custom_dir_label.set_halign(Gtk.Align.START)
        self.custom_dir_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self.custom_dir_label.set_max_width_chars(30)

        # Add widgets to the grid
        self.grid.attach(self.lang_label, 0, 0, 1, 1)
        self.grid.attach(self.lang_combo, 1, 0, 1, 1)
        self.grid.attach(self.theme_label, 0, 1, 1, 1)
        self.grid.attach(theme_box, 1, 1, 1, 1)
        self.grid.attach(self.dir_label, 0, 2, 1, 1)
        self.grid.attach(self.dir_combo, 1, 2, 1, 1)

        # Add a separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(separator, False, False, 10)

        # Add a switch for enabling/disabling notifications
        notifications_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        self.notifications_label = Gtk.Label(label=_("Enable notifications:"))
        self.notifications_label.set_halign(Gtk.Align.START)
        self.notifications_switch = Gtk.Switch()
        self.notifications_switch.set_active(current_settings["notifications_enabled"])
        self.notifications_switch.connect("notify::active", self.on_setting_changed)
        notifications_box.pack_start(self.notifications_label, False, False, 0)
        notifications_box.pack_end(self.notifications_switch, False, False, 0)
        box.pack_start(notifications_box, False, False, 0)

        # Add a switch for auto-removing converted files
        autoremove_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        self.autoremove_label = Gtk.Label(label=_("Auto-remove converted files:"))
        self.autoremove_label.set_halign(Gtk.Align.START)
        self.autoremove_switch = Gtk.Switch()
        self.autoremove_switch.set_active(current_settings["autoremove_converted"])
        self.autoremove_switch.connect("notify::active", self.on_setting_changed)
        autoremove_box.pack_start(self.autoremove_label, False, False, 0)
        autoremove_box.pack_end(self.autoremove_switch, False, False, 0)
        box.pack_start(autoremove_box, False, False, 0)

        self.show_all()
        self.on_dir_combo_changed(self.dir_combo)
        self.update_theme_icon()

    def on_dir_combo_changed(self, combo):
        show_custom = combo.get_active_id() == "custom"
        if show_custom:
            if self.custom_dir_button not in self.grid.get_children():
                self.grid.attach(self.custom_dir_button, 1, 3, 1, 1)
                self.grid.attach(self.custom_dir_label, 1, 4, 1, 1)
        else:
            if self.custom_dir_button in self.grid.get_children():
                self.grid.remove(self.custom_dir_button)
                self.grid.remove(self.custom_dir_label)

                self.resize(1, 1)

        self.grid.show_all()
        self.update_theme_icon()
        self.on_setting_changed(combo)

    def on_custom_dir_clicked(self, button):
        dialog = Gtk.FileChooserDialog(
            title=_("Select Custom Output Directory"),
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            folder_path = dialog.get_filename()
            self.custom_dir = folder_path
            self.custom_dir_label.set_text(folder_path)
            self.custom_dir_label.set_tooltip_text(folder_path)
            self.on_setting_changed(button)
        dialog.destroy()

    def on_setting_changed(self, widget, switch_gparam=None):
        # Update settings
        self.current_settings["language"] = self.lang_combo.get_active_id()
        self.current_settings["theme"] = self.theme_combo.get_active_id()
        self.current_settings["output_directory"] = self.dir_combo.get_active_id()
        self.current_settings["custom_directory"] = self.custom_dir
        self.current_settings["notifications_enabled"] = self.notifications_switch.get_active()
        self.current_settings["autoremove_converted"] = self.autoremove_switch.get_active()

        # Save and apply the new settings
        self.parent.save_settings()
        self.parent.apply_settings()

        if widget == self.lang_combo:
            self.update_texts()
            self.resize(1, 1)
        elif widget == self.theme_combo:
            self.update_theme_icon()

    def update_texts(self):
        # Update dialog title
        self.set_title(_("Preferences"))

        # Update labels
        self.lang_label.set_text(_("Language:"))
        self.theme_label.set_text(_("Theme:"))
        self.dir_label.set_text(_("Default output directory:"))
        self.custom_dir_button.set_label(_("Choose custom directory"))
        self.notifications_label.set_text(_("Enable notifications:"))
        self.autoremove_label.set_text(_("Auto-remove converted files:"))

        # Update combo box items
        self.update_combobox_texts(
            self.theme_combo,
            [("system", _("System default")), ("light", _("Light")), ("dark", _("Dark"))],
        )
        self.update_combobox_texts(
            self.dir_combo,
            [
                ("same", _("Same as input")),
                ("custom", _("Choose directory")),
                ("ask", _("Ask each time")),
            ],
        )

        # Update custom directory label if not selected
        if not self.current_settings["custom_directory"]:
            self.custom_dir_label.set_text(_("Not selected"))

        # Update tooltip
        if self.theme_icon.get_visible():
            gtk_theme = self.get_current_gtk_theme()
            tooltip_text = _("Current GTK theme: {gtk_theme}\n\n").format(gtk_theme=gtk_theme)
            tooltip_text += _(
                "Note: If you're unable to get a light theme, it may be due to your system's GTK theme settings."
            )
            self.theme_icon.set_tooltip_text(tooltip_text)

    def update_combobox_texts(self, combobox, new_texts):
        active_id = combobox.get_active_id()
        combobox.remove_all()
        for id, text in new_texts:
            combobox.append(id, text)
        combobox.set_active_id(active_id)

    def update_theme_icon(self):
        selected_theme = self.theme_combo.get_active_id()
        gtk_theme = self.get_current_gtk_theme()

        if selected_theme == "light":
            self.theme_icon.set_visible(True)
            tooltip_text = _("Current GTK theme: {gtk_theme}\n\n").format(gtk_theme=gtk_theme)
            tooltip_text += _(
                "Note: If you're unable to get a light theme, it may be due to your system's GTK theme settings."
            )
            self.theme_icon.set_tooltip_text(tooltip_text)
        else:
            self.theme_icon.set_visible(False)

    def get_current_gtk_theme(self):
        settings = Gtk.Settings.get_default()
        return settings.get_property("gtk-theme-name")


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
