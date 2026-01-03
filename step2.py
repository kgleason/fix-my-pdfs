#!/usr/bin/env python3
"""
Auto-tag PDFs with structure detection and metadata
Processes all PDFs in ocr-files/ directory and outputs to tagged-pdfs/
Requires: pip install pdfplumber pikepdf
"""

import pdfplumber
import pikepdf
from pikepdf import Pdf, Dictionary, Name, Array
import os
import re
from pathlib import Path
import glob


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
        print(f"  ⚠ Error checking text: {e}")
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
                print(f"  ✓ Existing title: {title}")
                return title
    except:
        pass

    # Use filename without extension
    title = Path(pdf_path).stem
    print(f"  ℹ No title found - using filename: {title}")
    return title


def process_single_pdf(pdf_path, output_path):
    """Add basic tag structure to a single PDF"""

    print(f"\n{'=' * 60}")
    print(f"Processing: {Path(pdf_path).name}")
    print(f"{'=' * 60}")

    # Check for extractable text
    has_text = has_extractable_text(pdf_path)

    if not has_text:
        print("  ⚠ Warning: No extractable text found!")
        print("  → Consider running ocrmypdf first")
    else:
        print("  ✓ PDF has extractable text")

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

    # Create structure tree root
    struct_tree_root = Dictionary(
        Type=Name.StructTreeRoot,
        K=Array()
    )

    # Add a Document element
    doc_element = Dictionary(
        Type=Name.StructElem,
        S=Name.Document,
        P=struct_tree_root,
        K=Array()
    )

    # Determine heading levels based on font size
    heading_blocks = [b for b in all_structures if b['type'] == 'heading']
    size_to_level = {}
    if heading_blocks:
        sizes = sorted(set(b.get('size', 0) for b in heading_blocks), reverse=True)
        size_to_level = {size: f'H{min(i + 1, 6)}' for i, size in enumerate(sizes)}

    # Track if we're in a list
    current_list = None

    # Add structure elements
    for block in all_structures:
        if block['type'] == 'heading':
            # Close any open list
            if current_list:
                doc_element.K.append(current_list)
                current_list = None

            level = size_to_level.get(block.get('size', 0), 'H1')
            elem = Dictionary(
                Type=Name.StructElem,
                S=Name(level),
                P=doc_element,
                K=Array()
            )
            doc_element.K.append(elem)

        elif block['type'] == 'table':
            # Close any open list
            if current_list:
                doc_element.K.append(current_list)
                current_list = None

            elem = Dictionary(
                Type=Name.StructElem,
                S=Name.Table,
                P=doc_element,
                K=Array()
            )
            doc_element.K.append(elem)

        elif block['type'] == 'list_item':
            # Create new list if needed
            if not current_list:
                current_list = Dictionary(
                    Type=Name.StructElem,
                    S=Name.L,  # List
                    P=doc_element,
                    K=Array()
                )

            # Add list item
            li = Dictionary(
                Type=Name.StructElem,
                S=Name.LI,  # List Item
                P=current_list,
                K=Array()
            )
            current_list.K.append(li)

        else:  # paragraph
            # Close any open list
            if current_list:
                doc_element.K.append(current_list)
                current_list = None

            elem = Dictionary(
                Type=Name.StructElem,
                S=Name.P,
                P=doc_element,
                K=Array()
            )
            doc_element.K.append(elem)

    # Close final list if open
    if current_list:
        doc_element.K.append(current_list)

    struct_tree_root.K.append(doc_element)
    pdf.Root.StructTreeRoot = struct_tree_root

    # Save
    pdf.save(output_path)
    print(f"  ✓ Saved to: {output_path}")
    print(f"  ✓ Title: {title}")


def process_directory(input_dir='ocr-files', output_dir='tagged-pdfs'):
    """Process all PDFs in input directory"""

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Find all PDF files
    pdf_files = glob.glob(os.path.join(input_dir, '*.pdf'))

    if not pdf_files:
        print(f"No PDF files found in '{input_dir}' directory")
        print(f"Please create the directory and add PDF files to process")
        return

    print(f"\n{'=' * 60}")
    print(f"PDF Auto-Tagger")
    print(f"{'=' * 60}")
    print(f"Input directory:  {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Found {len(pdf_files)} PDF(s) to process")

    # Process each PDF
    successful = 0
    failed = 0

    for i, pdf_path in enumerate(pdf_files, 1):
        try:
            filename = Path(pdf_path).name
            output_path = os.path.join(output_dir, filename)

            print(f"\n[{i}/{len(pdf_files)}] {filename}")
            process_single_pdf(pdf_path, output_path)
            successful += 1

        except Exception as e:
            failed += 1
            print(f"  ✗ Error processing {filename}: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Processing Complete")
    print(f"{'=' * 60}")
    print(f"✓ Successful: {successful}")
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
        print(f"Default: python auto_tag_pdf.py ocr-files tagged-pdfs")
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