"""Document chunking with section-aware splitting for policy text."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterator

from pydantic import BaseModel, Field


@dataclass
class Chunk:
    """A text chunk with metadata for retrieval."""

    text: str
    chunk_id: str
    doc_id: str
    section: str | None = None
    start_char: int = 0
    end_char: int = 0
    chunk_index: int = 0


class ChunkMetadata(BaseModel):
    """Metadata for a chunk stored in vector DB."""

    chunk_id: str
    doc_id: str
    section: str | None = None
    start_char: int
    end_char: int
    chunk_index: int
    text_preview: str = Field(..., max_length=200)


# Section header patterns for NCD policies
SECTION_PATTERNS = [
    re.compile(r"^(\d+\.\d+(?:\.\d+)?)\s*[-–]\s*(.+)$", re.MULTILINE),  # 80.5.1 - Title
    re.compile(r"^(Background|Authority|Definition|Coverage|Frequency|Beneficiaries|Noncovered|Claims|Processing)", re.IGNORECASE),
    re.compile(r"^={3,}$", re.MULTILINE),  # Section separators
]


def _detect_section(text: str) -> str | None:
    """Detect section title from text."""
    lines = text.strip().split("\n")[:3]  # Check first 3 lines
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Try section number pattern (80.5.1 - Title)
        match = SECTION_PATTERNS[0].search(line)
        if match:
            return f"{match.group(1)} - {match.group(2).strip()}"
        
        # Try keyword pattern
        if SECTION_PATTERNS[1].match(line):
            return line[:100]
    
    return None


def _generate_chunk_id(text: str, doc_id: str, chunk_index: int) -> str:
    """Generate deterministic chunk ID."""
    content = f"{doc_id}:{chunk_index}:{text[:100]}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def chunk_policy_text(
    text: str,
    doc_id: str,
    *,
    chunk_size: int = 512,
    overlap: int = 128,
    min_chunk_size: int = 100,
) -> list[Chunk]:
    """
    Chunk policy text with section awareness and overlap.
    
    Strategy:
    1. Split on section boundaries (headers, separators)
    2. Further split long sections into overlapping chunks
    3. Preserve section context in metadata
    
    Args:
        text: Policy text to chunk
        doc_id: Document identifier (e.g., "NCD_150.3")
        chunk_size: Target chunk size in characters
        overlap: Overlap between chunks in characters
        min_chunk_size: Minimum chunk size (discard smaller)
    
    Returns:
        List of Chunk objects with metadata
    """
    chunks: list[Chunk] = []
    chunk_index = 0
    
    # Split on major section boundaries first
    section_splits = re.split(r"\n={3,}\n", text)
    
    current_section = None
    char_offset = 0
    
    for section_text in section_splits:
        section_text = section_text.strip()
        if not section_text:
            continue
        
        # Detect section title
        detected_section = _detect_section(section_text)
        if detected_section:
            current_section = detected_section
        
        # Split long sections into chunks with overlap
        if len(section_text) <= chunk_size:
            # Small section: one chunk
            chunk_id = _generate_chunk_id(section_text, doc_id, chunk_index)
            chunks.append(
                Chunk(
                    text=section_text,
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    section=current_section,
                    start_char=char_offset,
                    end_char=char_offset + len(section_text),
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1
        else:
            # Large section: sliding window with overlap
            start = 0
            while start < len(section_text):
                end = min(start + chunk_size, len(section_text))
                chunk_text = section_text[start:end].strip()
                
                if len(chunk_text) >= min_chunk_size:
                    chunk_id = _generate_chunk_id(chunk_text, doc_id, chunk_index)
                    chunks.append(
                        Chunk(
                            text=chunk_text,
                            chunk_id=chunk_id,
                            doc_id=doc_id,
                            section=current_section,
                            start_char=char_offset + start,
                            end_char=char_offset + end,
                            chunk_index=chunk_index,
                        )
                    )
                    chunk_index += 1
                
                # Move window with overlap
                start += chunk_size - overlap
                if start >= len(section_text):
                    break
        
        char_offset += len(section_text) + 4  # +4 for separator
    
    return chunks


def chunk_iterator(
    chunks: list[Chunk],
) -> Iterator[tuple[str, ChunkMetadata]]:
    """
    Yield (text, metadata) pairs for vector store insertion.
    
    Args:
        chunks: List of Chunk objects
        
    Yields:
        (text, metadata) tuples
    """
    for chunk in chunks:
        metadata = ChunkMetadata(
            chunk_id=chunk.chunk_id,
            doc_id=chunk.doc_id,
            section=chunk.section,
            start_char=chunk.start_char,
            end_char=chunk.end_char,
            chunk_index=chunk.chunk_index,
            text_preview=chunk.text[:200],
        )
        yield chunk.text, metadata
