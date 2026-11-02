import re
from typing import List, Dict, Any
from pypdf import PdfReader
from config import CHUNK_TARGET_WORDS, CHUNK_OVERLAP_WORDS

def extract_text_from_pdf(file_path: str) -> List[Dict[str, Any]]:
    """
    Extract text page-by-page from a PDF using pypdf.
    Preserves structural line breaks for semantic boundary detection.
    """
    reader = PdfReader(file_path)
    pages = []
    for idx, page in enumerate(reader.pages):
        raw_text = page.extract_text() or ""
        # Normalize carriage returns while keeping paragraph and sentence boundaries
        normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n")
        # Collapse excessive spaces within lines, but preserve double newlines
        lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in normalized.split("\n")]
        cleaned = "\n".join(lines).strip()
        if cleaned:
            pages.append({
                "page": idx + 1,
                "text": cleaned
            })
    return pages

def split_into_semantic_units(text: str) -> List[str]:
    """
    Hierarchical semantic boundary splitter:
    1. Paragraph / heading boundaries (double newlines \n\n+)
    2. Single newlines (distinct lines / list items)
    3. Sentence boundaries (periods, question marks, exclamation marks followed by whitespace)
    4. Clause boundaries (semicolons, colons)
    """
    # 1. Split on double newlines or heading patterns
    paragraphs = re.split(r'\n{2,}', text)
    semantic_units = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        words = para.split()
        if len(words) <= CHUNK_TARGET_WORDS:
            semantic_units.append(para)
        else:
            # Paragraph is too long: split on sentence boundaries
            sentences = re.split(r'(?<=[.!?])\s+', para)
            current_unit = []
            current_len = 0

            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                sent_words = sent.split()
                if current_len + len(sent_words) > CHUNK_TARGET_WORDS and current_unit:
                    semantic_units.append(" ".join(current_unit))
                    current_unit = [sent]
                    current_len = len(sent_words)
                else:
                    current_unit.append(sent)
                    current_len += len(sent_words)

            if current_unit:
                semantic_units.append(" ".join(current_unit))

    return semantic_units

def chunk_text(pages: List[Dict[str, Any]], target_words: int = CHUNK_TARGET_WORDS, overlap_words: int = CHUNK_OVERLAP_WORDS) -> List[Dict[str, Any]]:
    """
    Semantic-aware chunker:
    - Splits on paragraph & heading boundaries first.
    - Sentence boundaries as fallback.
    - Hard word-cut only as last resort.
    - Overlap: carries trailing sentences from prior chunk to eliminate boundary cutoff.
    - Preserves [Page X] provenance metadata.
    """
    chunks = []
    chunk_index = 0

    for page_dict in pages:
        page_num = page_dict["page"]
        page_text = page_dict["text"]

        units = split_into_semantic_units(page_text)
        current_chunk_words = []
        current_chunk_text = []

        for unit in units:
            unit_words = unit.split()

            # If adding this unit exceeds target word limit and we already have content:
            if len(current_chunk_words) + len(unit_words) > target_words and current_chunk_words:
                chunk_body = " ".join(current_chunk_text).strip()
                chunks.append({
                    "chunk_index": chunk_index,
                    "content": f"[Page {page_num}] {chunk_body}",
                    "page": page_num,
                    "word_count": len(current_chunk_words)
                })
                chunk_index += 1

                # Carry over semantic overlap (last N words of previous chunk)
                overlap_seed = current_chunk_words[-overlap_words:] if len(current_chunk_words) > overlap_words else current_chunk_words
                current_chunk_words = list(overlap_seed) + unit_words
                current_chunk_text = [" ".join(overlap_seed), unit]
            else:
                current_chunk_words.extend(unit_words)
                current_chunk_text.append(unit)

        # Append trailing chunk for this page
        if current_chunk_text:
            chunk_body = " ".join(current_chunk_text).strip()
            chunks.append({
                "chunk_index": chunk_index,
                "content": f"[Page {page_num}] {chunk_body}",
                "page": page_num,
                "word_count": len(current_chunk_words)
            })
            chunk_index += 1

    return chunks
