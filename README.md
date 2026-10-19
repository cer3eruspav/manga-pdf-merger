# Manga PDF Merger

A command-line tool to sort PDF files by chapter numbers, remove known credit pages using reference image matching, and merge them into a single PDF.

> **Important Limitation:** This program does not use AI or OCR to automatically detect new credit pages. It only compares page images against the reference images stored in `credit_images`. If you encounter a new credit page format, you must add that page image as a reference before the program can recognize it.

## Features

- Sorts files by chapter numbers parsed from filenames and inserts chapter separator pages.
- Compares every page in the PDF against reference images, including those inside subfolders of `credit_images`.
- Automatically removes pages that match reference images before merging.
- If image verification fails, the program alerts the user and falls back to the original PDF without blindly deleting pages.

Matching is image-based rather than text-based, so it may not recognize credit pages that are cropped, rearranged, or heavily modified compared to the reference images. Providing multiple reference variations is recommended for better coverage.

## Requirements

- Windows
- Python 3.10 or higher
- [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows) (required for rendering PDF pages as images)

## Fresh Windows Installation

1. Install Python 3.10+ from [python.org](https://www.python.org/downloads/windows/) and make sure to check the option to install the Python Launcher (`py`).
2. Download and extract Poppler for Windows, then add the Poppler `Library\bin` folder to your Windows `PATH`, or update `POPPLER_PATH` in `merge_manga.py` to point to that directory.
3. Download or clone the program folder, keeping `merge_manga.py`, `run.bat`, and `credit_images` together.
4. Open PowerShell inside the program directory and install the required dependencies:

```powershell
py -3 -m pip install -r requirements.txt```
  <img width="1024" height="572" alt="สร้างshortcut 001" src="https://github.com/user-attachments/assets/b30d880b-4aab-4221-b84d-77be36d5009f" />
  <img width="1024" height="618" alt="สร้างshortcut 002" src="https://github.com/user-attachments/assets/a5773914-c775-4588-b4cb-c95e52d952c7" />
  <img width="1024" height="507" alt="สร้างshortcut 003" src="https://github.com/user-attachments/assets/868357d8-a882-4ecb-97d2-b952bd530873" />
  <img width="1024" height="373" alt="สร้างshortcut 004" src="https://github.com/user-attachments/assets/33f37eee-a10a-4f10-92d7-a210dd91d36b" />
  <img width="809" height="517" alt="001" src="https://github.com/user-attachments/assets/a279c599-961c-4e8c-8119-0ab046381b12" />
  <img width="472" height="327" alt="002" src="https://github.com/user-attachments/assets/b095569b-cac2-435a-8b18-4ead4ca5f691" />
  <img width="1310" height="816" alt="003" src="https://github.com/user-attachments/assets/3a1b09ba-3419-4554-88d6-e365f6809706" />
  <img width="1024" height="378" alt="004" src="https://github.com/user-attachments/assets/bebc1fb8-fdf6-403c-a506-64cd8f96fd1b" />

