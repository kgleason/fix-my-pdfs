# ============================================================================
# pdf_tagger.py - Core PDF Processing Class
# ============================================================================
"""
Core PDF tagging functionality.
"""
import ocrmypdf
import pdfplumber
import pikepdf
from pikepdf import Pdf, Dictionary, Name, Array
import re
from pathlib import Path
from typing import List, Optional
import queue

from models import PDFBlock, ProcessingMessage


class PDFTagger:
    """Handles PDF tagging operations for a single PDF file"""

    def __init__(self, input_path: str, output_path: str, tmp_path: str, job_id: str = None,
                 original_filename: str = None):
        self.input_path = input_path
        self.output_path = output_path
        self.tmp_path = tmp_path
        self.job_id = job_id
        self.original_filename = original_filename
        self.pdf: Optional[Pdf] = None
        self.structures: List[PDFBlock] = []
        self.message_queue = None

    def set_message_queue(self, msg_queue: queue.Queue):
        """Set the message queue for logging"""
        self.message_queue = msg_queue

    def log(self, message_type: str, message: str):
        """Send log message to queue if available, otherwise print"""
        msg = ProcessingMessage(type=message_type, message=message)
        if self.message_queue:
            self.message_queue.put(msg.to_dict())
        else:
            print(f"[{msg.timestamp}] {message}")

    def has_extractable_text(self) -> bool:
        """Check if PDF has extractable text"""
        try:
            with pdfplumber.open(self.input_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text and text.strip():
                        return True
            return False
        except Exception as e:
            self.log('error', f"Error checking text: {e}")
            return False

    def ocr_pdf(self, pdf_path: str, skip_text: bool = False) -> bool:
        """Perform OCR on the PDF"""
        try:
            self.log('info', "Running OCR on PDF...")
            ec = ocrmypdf.ocr(
                input_file=pdf_path,
                output_file=self.tmp_path,
                skip_text=skip_text
            )
            ret_bool = ec == 0 if isinstance(ec, int) else ec
            return ret_bool
        except ocrmypdf.exceptions.ColorConversionNeededError:
            self.log('info', "Color conversion needed, retrying...")
            return self.ocr_pdf(pdf_path=pdf_path, skip_text=skip_text)
        except ocrmypdf.MissingDependencyError as exc:
            self.log('warning', f"Missing OCR dependency: {exc.message}")
            return False
        except ocrmypdf.UnsupportedImageFormatError:
            self.log('warning', "Unsupported image format in PDF")
            return False
        except ocrmypdf.DpiError:
            self.log('warning', "DPI error in PDF")
            return False
        except ocrmypdf.OutputFileAccessError:
            self.log('warning', f"Unable to write OCR output file")
            return False
        except ocrmypdf.PriorOcrFoundError:
            self.log('info', "Prior OCR detected. Running with skip_text option")
            return self.ocr_pdf(pdf_path=pdf_path, skip_text=True)
        except ocrmypdf.SubprocessOutputError:
            self.log('warning', "OCR subprocess error")
            return False
        except (ocrmypdf.EncryptedPdfError, ocrmypdf.exceptions.DigitalSignatureError):
            self.log('warning', "PDF is signed or encrypted - cannot OCR")
            return False
        except ocrmypdf.exceptions.BadArgsError:
            self.log('warning', "Invalid OCR arguments")
            return False
        except ocrmypdf.exceptions.TaggedPDFError:
            self.log('warning', "PDF is already tagged - skipping OCR")
            return False
        except Exception as e:
            self.log('error', f"Unexpected OCR error: {str(e)}")
            return False

    def detect_lists(self, blocks: List[PDFBlock]) -> List[PDFBlock]:
        """Detect list items based on bullets or numbering"""
        list_patterns = [
            r'^[•●○▪▫■□◦⚫⚪]\s',
            r'^\d+\.\s',
            r'^[a-z]\.\s',
            r'^[ivx]+\.\s',
            r'^[-–—]\s',
        ]

        for block in blocks:
            text = block.text.strip()
            for pattern in list_patterns:
                if re.match(pattern, text, re.IGNORECASE):
                    block.type = 'list_item'
                    break

        return blocks

    def analyze_page_structure(self, page) -> List[PDFBlock]:
        """Detect headings, paragraphs, tables, and lists on a single page"""
        blocks = []

        tables = page.extract_tables()
        words = page.extract_words(extra_attrs=['fontname', 'size'])

        if not words:
            return blocks

        avg_size = sum(w['size'] for w in words) / len(words)

        # Group words into text blocks
        text_blocks = []
        current_block = []
        last_bottom = None

        for word in words:
            if last_bottom and word['top'] - last_bottom > 10:
                if current_block:
                    text_blocks.append(current_block)
                    current_block = []
            current_block.append(word)
            last_bottom = word['bottom']

        if current_block:
            text_blocks.append(current_block)

        # Add tables
        for table in tables:
            if table and len(table) > 0:
                blocks.append(PDFBlock(
                    type='table',
                    text=f'[Table with {len(table)} rows]',
                    data=table
                ))

        # Classify text blocks
        for block in text_blocks:
            avg_block_size = sum(w['size'] for w in block) / len(block)
            text = ' '.join(w['text'] for w in block)

            if avg_block_size > avg_size * 1.2 and len(text) < 150:
                blocks.append(PDFBlock(type='heading', text=text, size=avg_block_size))
            else:
                blocks.append(PDFBlock(type='paragraph', text=text))

        return blocks

    def analyze_structure(self):
        """Analyze the entire PDF structure"""
        with pdfplumber.open(self.input_path) as pdfp:
            page_count = len(pdfp.pages)
            self.log('info', f"Analyzing {page_count} pages...")

            for i, page in enumerate(pdfp.pages, 1):
                if i % 5 == 0 or i == page_count:
                    self.log('progress', f"Analyzing page {i}/{page_count}")
                page_structures = self.analyze_page_structure(page)
                self.structures.extend(page_structures)

        self.structures = self.detect_lists(self.structures)
        self._print_statistics()

    def _print_statistics(self):
        """Print statistics about found structures"""
        headings = sum(1 for s in self.structures if s.type == 'heading')
        paragraphs = sum(1 for s in self.structures if s.type == 'paragraph')
        tables = sum(1 for s in self.structures if s.type == 'table')
        lists = sum(1 for s in self.structures if s.type == 'list_item')

        self.log('info', f"Found {len(self.structures)} elements: {headings} headings, "
                         f"{paragraphs} paragraphs, {tables} tables, {lists} list items")

    def get_or_create_title(self, original_filename: str = None) -> str:
        """Get existing title or create from filename"""
        try:
            with self.pdf.open_metadata() as meta:
                if meta.get('dc:title'):
                    title = str(meta['dc:title'])
                    title = ' '.join(title.split())
                    self.log('info', f"Using existing title: {title}")
                    return title
        except:
            pass

        # Use original filename if provided, otherwise extract from path
        if original_filename:
            title = Path(original_filename).stem
        else:
            # Remove job ID prefix (UUID_filename.pdf -> filename.pdf)
            filename = Path(self.input_path).stem
            # Split on underscore and remove first part if it looks like a UUID
            parts = filename.split('_', 1)
            if len(parts) > 1 and len(parts[0]) == 36:  # UUID length
                title = parts[1]
            else:
                title = filename

        title = ' '.join(title.split())
        self.log('info', f"Using filename as title: {title}")
        return title

    def add_tags(self):
        """Add tag structure to the PDF"""
        self.log('info', "Adding accessibility tags...")

        if '/MarkInfo' not in self.pdf.Root:
            self.pdf.Root.MarkInfo = Dictionary(Marked=True)
        else:
            self.pdf.Root.MarkInfo.Marked = True

        struct_elems = []

        # Determine heading levels
        heading_blocks = [b for b in self.structures if b.type == 'heading']
        size_to_level = {}
        if heading_blocks:
            sizes = sorted(set(b.size for b in heading_blocks if b.size), reverse=True)
            size_to_level = {size: min(i + 1, 6) for i, size in enumerate(sizes)}

        current_list_items = []
        total = len(self.structures)

        for idx, block in enumerate(self.structures):
            if idx % 20 == 0 and idx > 0:
                self.log('progress', f"Creating tags: {idx}/{total} elements")

            try:
                if block.type == 'heading':
                    if current_list_items:
                        list_elem = self._create_list_element(current_list_items)
                        struct_elems.append(list_elem)
                        current_list_items = []

                    level_num = size_to_level.get(block.size, 1)
                    elem = self.pdf.make_indirect(Dictionary(
                        Type=Name.StructElem,
                        S=Name(f'/H{level_num}'),
                        K=Array()
                    ))
                    struct_elems.append(elem)

                elif block.type == 'table':
                    if current_list_items:
                        list_elem = self._create_list_element(current_list_items)
                        struct_elems.append(list_elem)
                        current_list_items = []

                    elem = self.pdf.make_indirect(Dictionary(
                        Type=Name.StructElem,
                        S=Name.Table,
                        K=Array()
                    ))
                    struct_elems.append(elem)

                elif block.type == 'list_item':
                    li = self.pdf.make_indirect(Dictionary(
                        Type=Name.StructElem,
                        S=Name.LI,
                        K=Array()
                    ))
                    current_list_items.append(li)

                else:  # paragraph
                    if current_list_items:
                        list_elem = self._create_list_element(current_list_items)
                        struct_elems.append(list_elem)
                        current_list_items = []

                    elem = self.pdf.make_indirect(Dictionary(
                        Type=Name.StructElem,
                        S=Name.P,
                        K=Array()
                    ))
                    struct_elems.append(elem)

            except Exception as e:
                self.log('warning', f"Could not create element {idx}: {str(e)}")
                continue

        if current_list_items:
            list_elem = self._create_list_element(current_list_items)
            struct_elems.append(list_elem)

        self.log('info', "Finalizing structure tree...")

        doc_element = self.pdf.make_indirect(Dictionary(
            Type=Name.StructElem,
            S=Name.Document,
            K=Array(struct_elems)
        ))

        struct_tree_root = Dictionary(
            Type=Name.StructTreeRoot,
            K=Array([doc_element])
        )

        self.pdf.Root.StructTreeRoot = struct_tree_root

    def _create_list_element(self, list_items: list):
        """Helper to create a list element"""
        return self.pdf.make_indirect(Dictionary(
            Type=Name.StructElem,
            S=Name.L,
            K=Array(list_items)
        ))

    def save(self):
        """Save the tagged PDF"""
        self.log('info', "Saving PDF...")

        try:
            self.pdf.save(
                self.output_path,
                compress_streams=False,
                stream_decode_level=pikepdf.StreamDecodeLevel.none,
                object_stream_mode=pikepdf.ObjectStreamMode.disable,
                linearize=False
            )
            self.log('success', f"PDF saved successfully")

        except Exception as e:
            self.log('error', f"Error saving PDF: {str(e)}")
            raise

    def process(self) -> bool:
        """Main processing pipeline"""
        try:
            # Check for extractable text
            has_text = self.has_extractable_text()

            if not has_text:
                self.log('warning', "No extractable text found - running OCR")
                is_processable = self.ocr_pdf(self.input_path)
                if not is_processable:
                    self.log('error', "OCR failed - cannot process PDF")
                    return False
                self.log('success', "OCR completed successfully")
                # Use the OCR'd file as input
                self.input_path = self.tmp_path
            else:
                self.log('info', "PDF has extractable text")

            # Open PDF
            self.pdf = Pdf.open(self.input_path)

            # Get/set title (pass original filename to avoid job ID in title)
            title = self.get_or_create_title(self.original_filename)
            with self.pdf.open_metadata() as meta:
                meta['dc:title'] = title

            # Process
            self.analyze_structure()
            self.add_tags()
            self.save()

            self.log('success', f"Processing complete! Title: {title}")
            return True

        except Exception as e:
            self.log('error', f"Processing failed: {str(e)}")
            return False

        finally:
            if self.pdf is not None:
                self.pdf.close()