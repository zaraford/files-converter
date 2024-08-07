<div align="center">
  <img src="./icons/hicolor/128x128/apps/files-converter.png" width="100px" />
  <h1>Files Converter</h1>
  <p>File conversion utility with context menu integration
Files Converter is a versatile file conversion utility that integrates
with the Nautilus file manager, allowing users to convert various file
types including photos, videos, vectors, audio, documents, and archives.</p>
</div>

## Supported formats

#### Photos: jpg, png, gif, bmp, tiff, webp
#### Videos: mp4, avi, mov, mkv, webm
#### Vectors: svg, eps, ai
#### Audio: mp3, wav, ogg, flac, aac
#### Documents: pdf, docx, txt, rtf, odt
#### Archives: zip, tar, gz, rar, 7z
#### Ebooks: epub, mobi, azw3, fb2, lit, txt, rtf, pdf

## Screenshot
<div align="center">
  <img src="https://github.com/user-attachments/assets/c02f72b2-61cc-4e76-b1b3-353589bfcb0a"/>
</div>

## Installation instructions
Ubuntu/Debian 
Install from deb package 

### Build from source
Build and install by running:
```
git clone https://github.com/zaraford/files-converter.git
cd files-converter
dpkg-buildpackage -us -uc -b
sudo dpkg -i ../files-converter_0.1.0-1_all.deb
sudo apt-get install -f
```
Can be removed with:
```
sudo dpkg -r files-converter
```
or:
```
sudo dpkg -purge files-converter
```
if you want delete configuration files too.

## Donations
Do you like the utility? Would you like to support its development? Feel free to donate.
<div>
  <a href='https://ko-fi.com/K3K1114UAG' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi2.png?v=3' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>
</div> 

## License
MIT
