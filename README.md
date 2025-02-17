<div align="center">
  <img src="./icons/hicolor/128x128/apps/files-converter.png" width="100px" />
  <h1>Files Converter</h1>
  <p>File conversion utility with context menu integration
Files Converter is a versatile file conversion utility that integrates
with the Nautilus file manager, allowing users to convert various file
types including photos, videos, vectors, audio, documents, and archives.</p>
</div>

## Master branch status

[![Scanning and test](https://github.com/zaraford/files-converter/actions/workflows/ci.yml/badge.svg)](https://github.com/zaraford/files-converter/actions/workflows/ci.yml)


## Supported formats

Photos: jpg, jpeg, png, gif, bmp, tiff, webp

Videos: mp4, avi, mov, mkv, webm

Vectors: svg, eps

Audio: mp3, wav, ogg, flac, aac

Documents: pdf, docx, txt, rtf, odt

Archives: zip, tar, gz, rar, 7z

Ebooks: epub, mobi, azw3, fb2, txt, rtf, pdf

## Screenshot
<div align="center">
  <img src="https://github.com/user-attachments/assets/c02f72b2-61cc-4e76-b1b3-353589bfcb0a"/>
</div>

## Installation instructions
### Preparation (Required Steps)
```
git clone https://github.com/zaraford/files-converter.git
cd files-converter
pip install -r requirements.txt
```
If you encounter issues with `pycairo`, you can resolve them by installing the following dependencies:
```
sudo apt-get update
sudo apt-get install -y libcairo2-dev pkg-config python3-dev libgirepository1.0-dev
```

### Ubuntu/Debian 

#### Install from `.deb` Package
To install Files Converter using the pre-built .deb package:
```
sudo dpkg -i files-converter_0.1.2-1_all.deb
sudo apt-get install -f
```
This will install any missing dependencies and complete the installation.
#### Build from Source
If you prefer to build and install the package from source, follow these steps:

1. Build the package:
```
dpkg-buildpackage -us -uc -b
```
2. Install the generated `.deb` file:
```
sudo dpkg -i ../files-converter_0.1.2-1_all.deb
sudo apt-get install -f
```
#### Uninstallation
You can remove Files Converter using:
```
sudo dpkg -r files-converter
```
To also remove configuration files:
```
sudo dpkg --purge files-converter
```
<!--
### Fedora/CentOS/RHEL
#### Install from `.rpm` Package
Install from `.rpm` package:
```
sudo rpm -i files-converter-0.1.2-2.noarch.rpm
```
#### Uninstallation
To remove the package:
```
sudo rpm -e files-converter
```
-->
### Flatpak (Coming Soon)
Files Converter will soon be available on Flathub, making installation easy across multiple Linux distributions. Stay tuned for updates.


## Donations
Do you like the utility? Would you like to support its development? Feel free to donate.
<div>
  <a href='https://ko-fi.com/K3K1114UAG' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi2.png?v=3' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>
</div> 

## License
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
