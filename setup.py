import os
import sys
from setuptools import find_packages, setup
from setuptools.command.install import install
from subprocess import check_call, CalledProcessError


def compile_translations():
    po_dir = "po"
    for po_file in os.listdir(po_dir):
        if po_file.endswith(".po"):
            lang = os.path.splitext(po_file)[0]
            mo_dir = f"locale/{lang}/LC_MESSAGES"
            os.makedirs(mo_dir, exist_ok=True)
            mo_file = f"{mo_dir}/files-converter.mo"
            po_path = f"{po_dir}/{po_file}"

            try:
                check_call(["msgfmt", "-o", mo_file, po_path])
                print(f"Compiled {po_file} successfully")
            except CalledProcessError as e:
                print(f"Error compiling {po_file}: {str(e)}", file=sys.stderr)


class CustomInstallCommand(install):
    def run(self):
        compile_translations()
        install.run(self)


def get_locale_files():
    data_files = []
    for root, dirs, files in os.walk("locale"):
        if "LC_MESSAGES" in root:
            mo_files = [os.path.join(root, f) for f in files if f.endswith(".mo")]
            if mo_files:
                path = os.path.join("/usr/share", root)
                data_files.append((path, mo_files))
    return data_files


def get_icon_files():
    icon_files = []
    for root, dirs, files in os.walk("icons"):
        for file in files:
            if file.endswith(".png"):
                icon_files.append((os.path.join("/usr/share", root), [os.path.join(root, file)]))
    return icon_files


setup(
    name="files-converter",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "Pillow",
        "ffmpeg-python",
        "python-docx",
        "PyPDF2",
        "pygobject",
        "pdf2docx",
        "striprtf",
        "odfpy",
        "packaging",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "files-converter=files_converter.__main__:main",
        ],
    },
    data_files=[
        ("share/applications", ["debian/files-converter.desktop"]),
        ("share/nautilus-python/extensions", ["src/files_converter/files_converter_extension.py"]),
    ]
    + get_icon_files()
    + get_locale_files(),
    cmdclass={
        "install": CustomInstallCommand,
    },
    author="Vladyslav Lodzhuk",
    author_email="vlad.lodgyk@gmail.com",
    description="A file conversion utility with context menu integration",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
)
