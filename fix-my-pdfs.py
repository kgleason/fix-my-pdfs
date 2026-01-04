#!/usr/bin/env python3
"""
Auto-tag PDFs with structure detection and metadata
Processes all PDFs in ocr-files/ directory and outputs to tagged-files/
Requires: pip install pdfplumber pikepdf
"""

import ocrmypdf
import pdfplumber
import pikepdf
from pikepdf import Pdf, Dictionary, Name, Array
import os
import re
from pathlib import Path


def has_extractable_text(pdf_path):
    """Check if PDF has extractable text"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text and text.strip():
                    return True
        return False
    except Exception as e:
        print(f"  ⚠️ Error checking text: {e}")
        return False


def detect_lists(blocks):
    """Detect list items based on bullets or numbering"""
    list_patterns = [
        r'^[•●○▪▫■□◦⚫⚪]\s',  # Bullet points
        r'^\d+\.\s',  # Numbered (1. 2. 3.)
        r'^[a-z]\.\s',  # Lettered (a. b. c.)
        r'^[ivx]+\.\s',  # Roman numerals
        r'^[-–—]\s',  # Dashes
    ]

    for block in blocks:
        text = block['text'].strip()
        for pattern in list_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                block['type'] = 'list_item'
                break

    return blocks


def analyze_text_structure(page):
    """Detect headings, paragraphs, tables, and lists"""
    # Extract tables first
    tables = page.extract_tables()
    table_bboxes = []

    # Get bounding boxes for tables to exclude from text analysis
    for table in tables:
        if table and len(table) > 0:
            # Approximate table bbox from cell positions
            # This is a simplified approach
            table_bboxes.append(None)  # Placeholder

    words = page.extract_words(extra_attrs=['fontname', 'size'])

    if not words:
        return []

    # Calculate average font size
    avg_size = sum(w['size'] for w in words) / len(words)

    # Group into text blocks
    blocks = []
    current_block = []
    last_bottom = None

    for word in words:
        # New block if significant vertical gap
        if last_bottom and word['top'] - last_bottom > 10:
            if current_block:
                blocks.append(current_block)
                current_block = []

        current_block.append(word)
        last_bottom = word['bottom']

    if current_block:
        blocks.append(current_block)

    # Classify blocks
    structured_blocks = []

    # Add tables
    for i, table in enumerate(tables):
        if table and len(table) > 0:
            structured_blocks.append({
                'type': 'table',
                'data': table,
                'text': f'[Table with {len(table)} rows]'
            })

    # Classify text blocks
    for block in blocks:
        avg_block_size = sum(w['size'] for w in block) / len(block)
        text = ' '.join(w['text'] for w in block)

        # Heading heuristic: larger than average + not too long
        if avg_block_size > avg_size * 1.2 and len(text) < 150:
            structured_blocks.append({'type': 'heading', 'text': text, 'size': avg_block_size})
        else:
            structured_blocks.append({'type': 'paragraph', 'text': text})

    # Detect lists
    structured_blocks = detect_lists(structured_blocks)

    return structured_blocks


def get_or_create_title(pdf_path, pdf):
    """Get existing title or create from filename"""
    # Check existing metadata
    try:
        with pdf.open_metadata() as meta:
            if meta.get('dc:title'):
                title = str(meta['dc:title'])
                # Clean up title - remove newlines and extra whitespace
                title = ' '.join(title.split())
                print(f"  ✅ Existing title: {title}")
                return title
    except:
        pass

    # Use filename without extension
    title = Path(pdf_path).stem
    # Clean up title - remove newlines and extra whitespace
    title = ' '.join(title.split())
    print(f"  ℹ️ No title found - using filename: {title}")
    return title

def ocr_single_pdf(pdf_path:str, output_path:str, pdf_type:str = 'pdfa', skip_text:bool = False):
    try:
        ret_bool = False
        ec = ocrmypdf.ocr(pdf_path, output_path, pdf_type=pdf_type, skip_text=skip_text)
        if isinstance(ec, int):
            ret_bool = True if ec == 0 else False
        elif isinstance(ec, bool):
            ret_bool = ec
        return ret_bool
    except ocrmypdf.exceptions.ColorConversionNeededError:
        print("  ℹ️ Info: Caught a color conversion exception. Outputting normal PDF")
        return ocr_single_pdf(pdf_path, output_path, 'pdf')
    except ocrmypdf.MissingDependencyError as exc:
        print(f"  ⚠️ Warning: Missing dependency detected: {exc.message}")
        return False
    except ocrmypdf.UnsupportedImageFormatError:
        print("  ⚠️ Warning: Unsupported image format")
        return False
    except ocrmypdf.DpiError:
        print("  ⚠️ Warning: Dpi Error")
        return False
    except ocrmypdf.OutputFileAccessError:
        print(f"  ⚠️ Warning: Unable to open output file {output_path}.")
        return False
    except ocrmypdf.PriorOcrFoundError:
        print("  ℹ️ Info: Prior OCR detected. Running with skip text")
        return ocr_single_pdf(pdf_path, output_path, pdf_type, True)
    except ocrmypdf.SubprocessOutputError:
        print("  ⚠️ Warning: Subprocess Error")
        return False
    except (ocrmypdf.EncryptedPdfError, ocrmypdf.exceptions.DigitalSignatureError):
        print(f"  ⚠️ Warning: File {pdf_path} is signed or encrypted. Cannot alter")
        return False
    except ocrmypdf.exceptions.BadArgsError:
        print("  ⚠️ Warning: Bad arguments passed to ocrmypdf.ocr()")
        return False
    except ocrmypdf.exceptions.TaggedPDFError:
        print(f"  ⚠️ Warning: File {pdf_path} is already tagged. Skipping")
        return False

def process_single_pdf(pdf_path, output_path):
    """Add basic tag structure to a single PDF"""

    # Check for extractable text
    has_text = has_extractable_text(pdf_path)
    is_processable = True

    if not has_text:
        print("  ⚠️ Warning: No extractable text found!")
        is_processable = ocr_single_pdf(pdf_path, output_path)
        if not is_processable:
            return None
        else:
            print("  ✅ PDF now has extractable text")
    else:
        print("  ✅ PDF has extractable text")

    # Open PDF
    pdf = Pdf.open(pdf_path)

    # Handle title metadata
    title = get_or_create_title(pdf_path, pdf)
    with pdf.open_metadata() as meta:
        meta['dc:title'] = title

    # Analyze structure with pdfplumber
    with pdfplumber.open(pdf_path) as pdfp:
        all_structures = []
        page_count = len(pdfp.pages)
        print(f"  Analyzing {page_count} pages...")

        for i, page in enumerate(pdfp.pages, 1):
            if i % 5 == 0 or i == page_count:
                print(f"    Page {i}/{page_count}")
            structures = analyze_text_structure(page)
            all_structures.extend(structures)

    # Print statistics
    headings = sum(1 for s in all_structures if s['type'] == 'heading')
    paragraphs = sum(1 for s in all_structures if s['type'] == 'paragraph')
    tables = sum(1 for s in all_structures if s['type'] == 'table')
    lists = sum(1 for s in all_structures if s['type'] == 'list_item')

    print(f"  Found {len(all_structures)} elements:")
    print(f"    • {headings} headings")
    print(f"    • {paragraphs} paragraphs")
    print(f"    • {tables} tables")
    print(f"    • {lists} list items")

    # Add tag structure
    print(f"  Adding tags...")

    # Mark as tagged
    if '/MarkInfo' not in pdf.Root:
        pdf.Root.MarkInfo = Dictionary(Marked=True)
    else:
        pdf.Root.MarkInfo.Marked = True

    # Create a simplified structure tree without explicit parent references
    # This avoids circular reference issues
    print(f"  Creating structure elements...")

    struct_elems = []

    # Determine heading levels based on font size
    heading_blocks = [b for b in all_structures if b['type'] == 'heading']
    size_to_level = {}
    if heading_blocks:
        sizes = sorted(set(b.get('size', 0) for b in heading_blocks), reverse=True)
        size_to_level = {size: min(i + 1, 6) for i, size in enumerate(sizes)}

    # Track if we're in a list
    current_list_items = []

    # Create structure elements
    for idx, block in enumerate(all_structures):
        if idx % 10 == 0 and idx > 0:
            print(f"    Processed {idx}/{len(all_structures)} elements...")

        try:
            if block['type'] == 'heading':
                # Close any open list first
                if current_list_items:
                    list_elem = pdf.make_indirect(Dictionary(
                        Type=Name.StructElem,
                        S=Name.L,
                        K=Array(current_list_items)
                    ))
                    struct_elems.append(list_elem)
                    current_list_items = []

                level_num = size_to_level.get(block.get('size', 0), 1)
                elem = pdf.make_indirect(Dictionary(
                    Type=Name.StructElem,
                    S=Name(f'/H{level_num}'),
                    K=Array()
                ))
                struct_elems.append(elem)

            elif block['type'] == 'table':
                # Close any open list first
                if current_list_items:
                    list_elem = pdf.make_indirect(Dictionary(
                        Type=Name.StructElem,
                        S=Name.L,
                        K=Array(current_list_items)
                    ))
                    struct_elems.append(list_elem)
                    current_list_items = []

                elem = pdf.make_indirect(Dictionary(
                    Type=Name.StructElem,
                    S=Name.Table,
                    K=Array()
                ))
                struct_elems.append(elem)

            elif block['type'] == 'list_item':
                # Add to current list
                li = pdf.make_indirect(Dictionary(
                    Type=Name.StructElem,
                    S=Name.LI,
                    K=Array()
                ))
                current_list_items.append(li)

            else:  # paragraph
                # Close any open list first
                if current_list_items:
                    list_elem = pdf.make_indirect(Dictionary(
                        Type=Name.StructElem,
                        S=Name.L,
                        K=Array(current_list_items)
                    ))
                    struct_elems.append(list_elem)
                    current_list_items = []

                elem = pdf.make_indirect(Dictionary(
                    Type=Name.StructElem,
                    S=Name.P,
                    K=Array()
                ))
                struct_elems.append(elem)
        except Exception as e:
            print(f"    ⚠️ Warning: Could not create element {idx} ({block['type']}): {e}")
            continue

    # Close final list if open
    if current_list_items:
        list_elem = pdf.make_indirect(Dictionary(
            Type=Name.StructElem,
            S=Name.L,
            K=Array(current_list_items)
        ))
        struct_elems.append(list_elem)

    print(f"  Finalizing structure tree...")

    # Create document element with all children
    doc_element = pdf.make_indirect(Dictionary(
        Type=Name.StructElem,
        S=Name.Document,
        K=Array(struct_elems)
    ))

    # Create structure tree root
    struct_tree_root = Dictionary(
        Type=Name.StructTreeRoot,
        K=Array([doc_element])
    )

    pdf.Root.StructTreeRoot = struct_tree_root

    # Save
    print(f"  Saving PDF (this may take a moment for large files)...")
    import signal

    class TimeoutError(Exception):
        pass

    def timeout_handler(signum, frame):
        raise TimeoutError("Save operation timed out")

    # Set up timeout (30 seconds)
    if hasattr(signal, 'SIGALRM'):  # Unix only
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)

    try:
        # Try minimal save options
        pdf.save(output_path,
                 compress_streams=False,
                 stream_decode_level=pikepdf.StreamDecodeLevel.none,
                 object_stream_mode=pikepdf.ObjectStreamMode.disable,
                 linearize=False)

        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)  # Cancel alarm

    except TimeoutError:
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)
        print(f"    ⚠️ Save timed out - trying without structure tree...")
        # Remove structure tree and try again
        if hasattr(pdf.Root, 'StructTreeRoot'):
            del pdf.Root.StructTreeRoot
        pdf.save(output_path, compress_streams=False)
        print(f"    ⚠️ Saved without structure tags due to timeout")
        return
    except Exception as e:
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)
        print(f"    Error during save: {e}")
        raise

    print(f"  ✅ Saved to: {output_path}")
    print(f"  ✅ Title: {title}")


def process_directory(input_dir='ocr-files', output_dir='tagged-files'):
    """Process all PDFs in input directory"""

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Find all PDF files using os.listdir to avoid glob issues with special chars
    try:
        all_files = os.listdir(input_dir)
        pdf_files = sorted([os.path.join(input_dir, f) for f in all_files if f.lower().endswith('.pdf')])
    except Exception as e:
        print(f"Error reading directory: {e}")
        return

    if not pdf_files:
        print(f"No PDF files found in '{input_dir}' directory")
        print(f"Please create the directory and add PDF files to process")
        return

    # Calculate max filename length for formatting (using sanitized names)
    max_name_len = max(len(' '.join(Path(pdf).name.split())) for pdf in pdf_files)
    separator_len = max(60, max_name_len + 20)

    print(f"\n{'=' * separator_len}")
    print(f"PDF Auto-Tagger")
    print(f"{'=' * separator_len}")
    print(f"Input directory:  {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Found {len(pdf_files)} PDF(s) to process")

    # Process each PDF
    successful = 0
    failed = 0

    for i, pdf_path in enumerate(pdf_files, 1):
        try:
            filename = Path(pdf_path).name
            # Clean filename for display (remove any embedded newlines/whitespace)
            display_filename = ' '.join(filename.split())

            # Sanitize output filename (replace problematic characters)
            safe_filename = filename.replace('\n', ' ').replace('\r', ' ')
            # Collapse multiple spaces
            safe_filename = ' '.join(safe_filename.split())

            output_path = os.path.join(output_dir, safe_filename)

            # Calculate dynamic separator based on filename length
            display_separator_len = max(60, len(display_filename) + 10)

            print(f"\n{'=' * display_separator_len}")
            print(f"[{i}/{len(pdf_files)}] {display_filename}")
            print(f"{'=' * display_separator_len}")

            process_single_pdf(pdf_path, output_path)
            successful += 1

        except Exception as e:
            failed += 1
            print(f"  ✗ Error processing {display_filename}: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print(f"\n{'=' * separator_len}")
    print(f"Processing Complete")
    print(f"{'=' * separator_len}")
    print(f"✅ Successful: {successful}")
    if failed > 0:
        print(f"✗ Failed:     {failed}")
    print(f"\nTagged PDFs saved to: {output_dir}/")
    print(f"\nNote: This creates basic tag structures.")
    print(f"For full accessibility, consider additional validation with PAC.")


if __name__ == "__main__":
    import sys

    # Allow optional directory arguments
    if len(sys.argv) >= 2:
        input_dir = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) >= 3 else 'tagged-files'
    else:
        input_dir = 'ocr-files'
        output_dir = 'tagged-files'

    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist")
        print(f"\nUsage: python auto_tag_pdf.py [input_dir] [output_dir]")
        print(f"Default: python auto_tag_pdf.py ocr-files tagged-files")
        sys.exit(1)

    try:
        process_directory(input_dir, output_dir)
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)