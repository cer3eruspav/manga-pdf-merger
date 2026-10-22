# Manga PDF Merger

A command-line tool to sort PDF files by chapter numbers, remove known credit pages using reference image matching, and merge them into a single PDF.

> **Important Limitation:** This program does not use AI or OCR to automatically detect new credit pages. It only compares page images against the reference images stored in `credit_images`. If you en[...] 

## Features

- Drag-and-drop integration: Supports dragging PDF files onto run.bat (or its shortcut) for quick execution.
- Sorts files by chapter numbers parsed from filenames and inserts chapter separator pages.
- Compares every page in the PDF against reference images, including those inside subfolders of `credit_images`.
- Automatically removes pages that match reference images before merging.
- If image verification fails, the program alerts the user and falls back to the original PDF without blindly deleting pages.

Matching is image-based rather than text-based, so it may not recognize credit pages that are cropped, rearranged, or heavily modified compared to the reference images. Providing multiple referenc[...]

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


## Creating a Windows shortcut (quick usage)

If you want an easy drag-and-drop way to run the merger on a folder of chapter PDFs, create a Windows shortcut that points to `run.bat` and then copy that shortcut into each series folder.

Steps (English):

1. In the program folder, right-click an empty area, choose "New" → "Shortcut".
2. When the Create Shortcut dialog opens, browse to and select `run.bat` (or type its full path), then click "Next".
3. Give the shortcut a name such as `PDFMerge` and click "Finish".
4. Copy the created `PDFMerge` shortcut.
5. Navigate to a folder that contains your manga series PDFs, right-click an empty area and choose "Paste" to place the shortcut in that folder.
6. To merge, select the chapter PDF files (for example `TEST ep 01` through `TEST ep 05`) and drag them onto the `PDFMerge` shortcut. The program will run using the files you dropped.

Key points:

- The shortcut MUST be in the same folder as the manga PDFs you want to merge.
- You can create multiple shortcut copies and place each inside different series folders so you don't have to move files around.

ขั้นตอน (ภาษาไทย):

1. ในโฟลเดอร์โปรแกรม ให้คลิกขวาที่พื้นที่ว่าง แล้วเลือก "New" → "Shortcut" (สร้างช็อตคัต).
2. ในหน้าต่าง Create Shortcut ให้เลื่อนหาและระบุตำแหน่งไฟล์ `run.bat` แล้วกด "Next".
3. ตั้งชื่อช็อตคัตเป็นตัวอย่างเช่น `PDFMerge` แล้วกด "Finish".
4. คัดลอกช็อตคัต `PDFMerge` ที่สร้างขึ้น.
5. ไปยังโฟลเดอร์ที่เก็บไฟล์ PDF ซีรีส์มังงะของคุณ คลิกขวาที่พื้นที่ว่างแล้วเลือก "Paste" เพื่อวางช็อตคัตไว้ที่นั่น.
6. เมื่อต้องการรวมไฟล์ ให้เลือกไฟล์บท (เช่น `TEST ep 01` ถึง `TEST ep 05`) แล้วลากมาวางบนช็อตคัต `PDFMerge` โปรแกรมจะรันกับไฟล์ที่คุณวางไว้.

ข้อควรทราบ:

- ช็อตคัตต้องอยู่ในโฟลเดอร์เดียวกับไฟล์ PDF มังงะเพื่อให้การทำงานถูกต้อง.
- สามารถสร้างช็อตคัตหลายๆ อันและวางไว้ในแต่ละโฟลเดอร์ซีรีส์ได้เพื่อความสะดวก.

