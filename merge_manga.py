import sys
import os
import re
import tempfile
from pypdf import PdfReader, PdfWriter, PdfMerger
from send2trash import send2trash
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image, ImageChops
from pdf2image import convert_from_path

# ==========================================
# กำหนด path ของ Poppler ที่คุณแตกไฟล์ไว้
# ==========================================
POPPLER_PATH = r"D:\AI\Envs\poppler\Library\bin"
CREDIT_MATCH_SIZE = (96, 128)
CREDIT_MATCH_THRESHOLD = 0.12
CREDIT_BACKGROUND_THRESHOLD = 245
PDF_RENDER_BATCH_SIZE = 16
MERGE_SIZE_TOLERANCE = 0.10

def create_separator_page(text):
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    temp_pdf.close()

    c = canvas.Canvas(temp_pdf.name, pagesize=letter)
    width, height = letter

    try:
        thai_font_path = "C:\\Windows\\Fonts\\tahoma.ttf"
        if os.path.exists(thai_font_path):
            pdfmetrics.registerFont(TTFont('ThaiFont', thai_font_path))
            c.setFont('ThaiFont', 28)
        else:
            c.setFont("Helvetica-Bold", 28)
    except Exception:
        c.setFont("Helvetica-Bold", 28)

    c.drawCentredString(width / 2.0, height / 2.0, text)
    c.save()

    return temp_pdf.name

def load_credit_images(credit_dir):
    credit_images = []
    if os.path.exists(credit_dir):
        for root, dirs, files in os.walk(credit_dir):
            dirs.sort()
            for file in sorted(files):
                if not file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    continue
                img_path = os.path.join(root, file)
                try:
                    with Image.open(img_path) as source:
                        img = _prepare_match_image(source)
                    credit_images.append(img)
                except (OSError, ValueError) as e:
                    print(f"[คำเตือน] ไม่สามารถโหลดภาพอ้างอิง {img_path}: {e}")
    return credit_images

def _prepare_match_image(image):
    return image.convert('L').resize(CREDIT_MATCH_SIZE, Image.Resampling.LANCZOS)

def is_credit_page(page_img, credit_images):
    if not credit_images:
        return False

    page_processed = _prepare_match_image(page_img)

    for c_img in credit_images:
        reference_processed = c_img
        if c_img.mode != 'L' or c_img.size != CREDIT_MATCH_SIZE:
            reference_processed = _prepare_match_image(c_img)

        difference = ImageChops.difference(page_processed, reference_processed)
        reference_or_page = ImageChops.darker(page_processed, reference_processed)
        active_pixels = sum(
            reference_or_page.histogram()[:CREDIT_BACKGROUND_THRESHOLD]
        )
        if not active_pixels:
            continue
        difference_histogram = difference.histogram()
        mean_difference = sum(
            value * count for value, count in enumerate(difference_histogram)
        ) / (active_pixels * 255)
        if mean_difference <= CREDIT_MATCH_THRESHOLD:
            return True

    return False

def remove_credit_pages(pdf_path, credit_images):
    if not credit_images:
        return pdf_path, 0

    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        if total_pages == 0:
            return pdf_path, 0

        pages_to_skip = set()
        poppler_path = POPPLER_PATH if os.path.isdir(POPPLER_PATH) else None
        for batch_start in range(0, total_pages, PDF_RENDER_BATCH_SIZE):
            batch_end = min(batch_start + PDF_RENDER_BATCH_SIZE, total_pages)
            images = convert_from_path(
                pdf_path,
                dpi=80,
                poppler_path=poppler_path,
                first_page=batch_start + 1,
                last_page=batch_end,
            )
            if len(images) != batch_end - batch_start:
                raise RuntimeError(
                    f"Expected {batch_end - batch_start} rendered pages, got {len(images)}"
                )

            for offset, page_img in enumerate(images):
                if is_credit_page(page_img, credit_images):
                    pages_to_skip.add(batch_start + offset)

        if not pages_to_skip or len(pages_to_skip) == total_pages:
            if len(pages_to_skip) == total_pages:
                print(f"[คำเตือน] ไม่ลบหน้าใดจาก {pdf_path}: ทุกหน้าตรงกับภาพอ้างอิง")
            return pdf_path, 0

        writer = PdfWriter()
        for idx, page in enumerate(reader.pages):
            if idx not in pages_to_skip:
                writer.add_page(page)

        temp_clean_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_clean_pdf.close()
        try:
            with open(temp_clean_pdf.name, 'wb') as f:
                writer.write(f)
        except Exception:
            os.remove(temp_clean_pdf.name)
            raise

        return temp_clean_pdf.name, len(pages_to_skip)
    except Exception as e:
        print(f"[คำเตือน] ตรวจหาหน้าเครดิตใน {pdf_path} ไม่สำเร็จ; ใช้ไฟล์เดิม: {e}")
        return pdf_path, 0

def get_available_output_path(output_path, input_files):
    input_paths = {os.path.normcase(os.path.abspath(path)) for path in input_files}
    output_dir = os.path.dirname(os.path.abspath(output_path))
    stem, extension = os.path.splitext(os.path.basename(output_path))
    candidate = output_path
    suffix = 2

    while (
        os.path.normcase(os.path.abspath(candidate)) in input_paths
        or os.path.exists(candidate)
    ):
        candidate = os.path.join(output_dir, f"{stem} ({suffix}){extension}")
        suffix += 1

    return candidate

def write_and_validate_merge(files_to_merge, output_path):
    expected_page_count = sum(len(PdfReader(path).pages) for path in files_to_merge)
    expected_input_size = sum(os.path.getsize(path) for path in files_to_merge)
    if expected_page_count == 0:
        raise ValueError("ไม่สามารถรวม PDF ที่ไม่มีหน้าได้")
    if expected_input_size == 0:
        raise ValueError("ไฟล์ PDF ต้นทางว่างเปล่า")

    output_dir = os.path.dirname(output_path)
    temp_output = tempfile.NamedTemporaryFile(
        delete=False, suffix='.pdf', dir=output_dir
    )
    temp_output.close()
    merger = PdfMerger()
    try:
        for path in files_to_merge:
            merger.append(path)
        merger.write(temp_output.name)
        merger.close()

        output_size = os.path.getsize(temp_output.name)
        if output_size == 0:
            raise ValueError("ไฟล์ PDF ผลลัพธ์ว่างเปล่า")

        with open(temp_output.name, 'rb') as output_file:
            actual_page_count = len(PdfReader(output_file).pages)
        if actual_page_count != expected_page_count:
            raise ValueError(
                f"จำนวนหน้าในไฟล์ผลลัพธ์ไม่ตรงกัน "
                f"(คาดว่า {expected_page_count}, ได้ {actual_page_count})"
            )

        size_difference = abs(output_size - expected_input_size) / expected_input_size
        if size_difference > MERGE_SIZE_TOLERANCE:
            raise ValueError(
                f"ขนาดไฟล์ผลลัพธ์ต่างจากขนาดรวมของ PDF ที่นำมารวม "
                f"{size_difference:.1%} (ยอมรับได้ไม่เกิน "
                f"{MERGE_SIZE_TOLERANCE:.0%})"
            )

        os.rename(temp_output.name, output_path)
        return output_size, actual_page_count, expected_input_size
    except Exception:
        try:
            merger.close()
        except Exception:
            pass
        if os.path.exists(temp_output.name):
            os.remove(temp_output.name)
        raise

def parse_manga_info(filename_full):
    name_without_ext = os.path.splitext(filename_full)[0]

    is_special = False
    special_pattern = (
        r'ตอนพิเศษ|(?<!\w)(?:special|extra)(?!\w)(?:\s*[-_]\s*.*)?$'
    )
    is_special = re.search(special_pattern, name_without_ext, re.IGNORECASE) is not None

    base_title = name_without_ext
    ep_num = None
    sub_title = ""

    if is_special:
        parts = re.split(special_pattern, name_without_ext, flags=re.IGNORECASE)
        base_title = parts[0].strip().rstrip('-').strip()
    else:
        # รูปแบบที่ 1: มีคำบอกตอน ไม่จำเป็นต้องมีขีดคั่น (แก้ปัญหาตาบอดแล้ว!)
        pattern1 = r'^(.*?)\s*(?:[-_]\s*)?(?:ตอนที่|ตอน|บทที่|เล่มที่|เล่ม|chapter|\bch\.?\b|episode|\bep\.?\b|round|\brd\.?\b|part|\bvol\.?\b|volume|section|act|book)\s*(\d+(?:\.\d+)?)(.*)$'
        match = re.search(pattern1, name_without_ext, re.IGNORECASE)

        if not match:
            # รูปแบบที่ 2: ไม่มีคำบอกตอน แต่มีขีดคั่น
            pattern2 = r'^(.*?)\s*[-_]\s*(\d+(?:\.\d+)?)(.*)$'
            match = re.search(pattern2, name_without_ext, re.IGNORECASE)

        if not match:
            # รูปแบบที่ 3: เว้นวรรคแล้วตามด้วยเลขตอนเลย
            pattern3 = r'^(.*?)\s+(\d+(?:\.\d+)?)\s*(\[?จบ\]?)?$'
            match = re.search(pattern3, name_without_ext, re.IGNORECASE)

        if match:
            base_title = match.group(1).strip()
            ep_str = match.group(2)
            raw_sub = match.group(3) if len(match.groups()) >= 3 else ""

            if ep_str:
                ep_num = float(ep_str)

            sub_title = re.sub(r'\[?\s*จบ\s*\]?', '', raw_sub).strip().lstrip('-').strip()
        else:
            # กรณีฉุกเฉินสุดๆ หาตัวเลขชุดสุดท้ายในชื่อไฟล์เพื่อป้องกันการเป็น 0
            nums = re.findall(r'\d+(?:\.\d+)?', name_without_ext)
            if nums:
                ep_num = float(nums[-1])
                base_title = re.sub(str(nums[-1]) + r'.*$', '', base_title).strip().rstrip('-').strip()

    # จัดการชื่อผู้เขียน [...]
    author_match = re.match(r'^(\s*\[[^\]]+\])', base_title)
    author_prefix = author_match.group(1).strip() if author_match else ""

    if "_" in base_title:
        parts_underscore = base_title.split("_", 1)
        eng_part = parts_underscore[1].strip()
        if author_prefix:
            base_title = f"{author_prefix} {eng_part}"
        else:
            base_title = eng_part

    # ล้างขยะท้ายชื่ออีกหนึ่งรอบ ป้องกันขีดหรือคำตกค้าง
    base_title = re.sub(r'\s+(?:ตอนที่|ตอน|chapter|ep)\s*$', '', base_title, flags=re.IGNORECASE).strip().rstrip('-').strip()

    return base_title, ep_num, is_special, sub_title

def merge_manga():
    if len(sys.argv) < 2:
        print("กรุณาลากไฟล์ PDF มาวางบน Script")
        return

    input_files = [f for f in sys.argv[1:] if os.path.exists(f) and f.lower().endswith('.pdf')]

    if not input_files:
        print("[ข้อผิดพลาด]: ไม่พบไฟล์ PDF ที่ถูกต้อง")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    credit_dir = os.path.join(script_dir, "credit_images")
    credit_images = load_credit_images(credit_dir)

    file_info_list = []
    for f in input_files:
        fname = os.path.basename(f)
        b_title, ep_n, is_sp, s_title = parse_manga_info(fname)
        file_info_list.append({
            'path': f,
            'base_title': b_title,
            'ep_num': ep_n if ep_n is not None else 0.0,
            'is_special': is_sp,
            'sub_title': s_title,
            'filename': fname
        })

    file_info_list = sorted(file_info_list, key=lambda x: (1 if x['is_special'] else 0, x['ep_num']))

    base_title = file_info_list[0]['base_title'] if file_info_list else "Manga"
    ep_numbers = []
    has_intro = False
    has_special = False
    is_finished = False
    total_input_size = 0
    total_deleted_credits = 0

    print("กำลังตรวจสอบและรวมไฟล์ด้วยระบบอัจฉริยะ...")

    files_to_merge = []
    temp_files_to_clean = []
    last_ep = None
    has_printed_first_sep = False

    for item in file_info_list:
        file_path = item['path']
        current_ep = item['ep_num']
        is_sp = item['is_special']
        sub_title = item['sub_title']
        filename_lower = item['filename'].lower()

        if "จบ" in filename_lower or is_sp:
            is_finished = True

        if is_sp:
            has_special = True
        else:
            ep_numbers.append(current_ep)
            if current_ep == 0.0:
                has_intro = True

        cleaned_pdf_path, deleted_count = remove_credit_pages(file_path, credit_images)
        total_deleted_credits += deleted_count

        if cleaned_pdf_path != file_path:
            temp_files_to_clean.append(cleaned_pdf_path)

        should_create_sep = False
        if is_sp:
            should_create_sep = True
            sep_text = "ตอนพิเศษ"
            if sub_title:
                sep_text += f" : {sub_title}"
        else:
            if not has_printed_first_sep:
                should_create_sep = True
                has_printed_first_sep = True
            elif current_ep != last_ep:
                should_create_sep = True

            if should_create_sep:
                ep_display = int(current_ep) if current_ep.is_integer() else current_ep

                prefix_label = "ตอนที่"
                if "chapter" in filename_lower or re.search(r'\bch\.?\b', filename_lower):
                    prefix_label = "Chapter"
                elif "episode" in filename_lower or re.search(r'\bep\.?\b', filename_lower):
                    prefix_label = "Episode"
                elif "round" in filename_lower or re.search(r'\brd\.?\b', filename_lower):
                    prefix_label = "Round"
                elif "part" in filename_lower:
                    prefix_label = "Part"
                elif "vol" in filename_lower or "volume" in filename_lower:
                    prefix_label = "Vol"

                if current_ep == 0.0 and not any(kw in filename_lower for kw in ["chapter", "ep", "round", "part", "vol", "ตอนที่", "บทที่", "ตอน"]):
                    sep_text = "บทนำ"
                else:
                    sep_text = f"{prefix_label} {ep_display}"

                if sub_title:
                    sep_text += f" : {sub_title}"

        if should_create_sep:
            sep_pdf_path = create_separator_page(sep_text)
            files_to_merge.append(sep_pdf_path)
            temp_files_to_clean.append(sep_pdf_path)

        files_to_merge.append(cleaned_pdf_path)
        if not is_sp:
            last_ep = current_ep

        try:
            total_input_size += os.path.getsize(file_path)
        except Exception:
            pass

    # ระบบสร้างชื่อไฟล์ผลลัพธ์ ควบคุมความเป๊ะ
    ep_str = ""
    if ep_numbers:
        min_ep = min(ep_numbers)
        max_ep = max(ep_numbers)

        prefix_label = "ตอนที่"
        sample_fn = file_info_list[0]['filename'].lower()
        if "chapter" in sample_fn or re.search(r'\bch\.?\b', sample_fn):
            prefix_label = "Chapter"
        elif "episode" in sample_fn or re.search(r'\bep\.?\b', sample_fn):
            prefix_label = "Episode"
        elif "round" in sample_fn or re.search(r'\brd\.?\b', sample_fn):
            prefix_label = "Round"
        elif "part" in sample_fn:
            prefix_label = "Part"
        elif "vol" in sample_fn or "volume" in sample_fn:
            prefix_label = "Vol"

        min_str = f"{min_ep:g}" if min_ep.is_integer() else f"{min_ep}"
        max_str = f"{max_ep:g}" if max_ep.is_integer() else f"{max_ep}"

        if min_ep == max_ep:
            ep_str = f"{prefix_label} {min_str}"
        else:
            ep_str = f"{prefix_label} {min_str}-{max_str}"

    if has_special:
        if ep_str:
            ep_str += "+พิเศษ"
        else:
            ep_str = "ตอนพิเศษ"
        is_finished = True

    if is_finished:
        if not ep_str.endswith("[จบ]"):
            ep_str += "[จบ]"

    if not ep_str:
        ep_str = "[จบ]"

    output_filename = f"{base_title} {ep_str}.pdf"
    output_path = os.path.join(os.path.dirname(input_files[0]), output_filename)
    output_path = get_available_output_path(output_path, input_files)

    print(f"\nกำลังรวมการ์ตูน: {os.path.basename(output_path)}...")

    is_success = False
    try:
        output_size, output_page_count, merge_input_size = write_and_validate_merge(
            files_to_merge, output_path
        )
        is_success = True
    except Exception as e:
        print(f"\n[เกิดข้อผิดพลาด]: {e}")

    for tmp in temp_files_to_clean:
        try:
            os.remove(tmp)
        except Exception as e:
            print(f"[คำเตือน] ลบไฟล์ชั่วคราว {tmp} ไม่สำเร็จ: {e}")

    if is_success:
        print(f"\nรวมไฟล์สำเร็จ! บันทึกที่: {output_path}")
        print(
            f"ตรวจสอบแล้ว {output_page_count} หน้า | "
            f"ขนาดต้นฉบับรวม {total_input_size:,} bytes | "
            f"ขนาด PDF ที่นำมารวม {merge_input_size:,} bytes | "
            f"ขนาดผลลัพธ์ {output_size:,} bytes "
            f"(ต่าง {abs(output_size - merge_input_size) / merge_input_size:.1%})"
        )
        print(f"กำลังย้ายไฟล์ต้นฉบับไปถังขยะ...")
        failed_trash = []
        for item in file_info_list:
            try:
                send2trash(item['path'])
            except OSError as e:
                failed_trash.append((item['path'], e))
        if failed_trash:
            print("[คำเตือน] รวมไฟล์สำเร็จ แต่ย้ายไฟล์ต้นฉบับบางไฟล์ไปถังขยะไม่สำเร็จ:")
            for path, error in failed_trash:
                print(f"  {path}: {error}")
    else:
        print(f"\n[ระบบความปลอดภัย]: การรวมไฟล์ล้มเหลว ยกเลิกการลบไฟล์ต้นฉบับ")

if __name__ == "__main__":
    merge_manga()
