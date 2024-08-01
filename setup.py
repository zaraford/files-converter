import os

from setuptools import find_packages, setup


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
        "python-nautilus",
        "calibre",
        "python-magic",
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
    + get_icon_files(),
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
