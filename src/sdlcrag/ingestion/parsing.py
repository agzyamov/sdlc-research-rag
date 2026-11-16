"""PDF → chunked LangChain Documents with Docling (via `langchain-docling`).

arXiv PDFs are born-digital, so OCR is off and tables use TableFormer's fast mode. Chunks come
from Docling's structure-aware HybridChunker, sized with the embedding model's tokenizer.
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from docling.chunking import HybridChunker
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableFormerMode,
    TableStructureOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from langchain_core.documents import Document
from langchain_docling import DoclingLoader
from langchain_docling.loader import BaseMetaExtractor, ExportType

from sdlcrag.core.config import get_settings
from sdlcrag.core.models import Modality
from sdlcrag.ingestion.multimodal.figures import (
    ensure_vision_reachable,
    picture_description_options,
)

CHUNK_MAX_TOKENS = 512
# Bibliographies are full of benchmark/model names but carry no findings: they would win
# keyword matches and crowd out real content, so they are not indexed.
NON_CONTENT_HEADING = re.compile(r"^\s*(\d+\.?\s*)?(references|bibliography)\b", re.IGNORECASE)


class CompactMetaExtractor(BaseMetaExtractor):
    """Keep only what retrieval needs (section, page, modality) instead of Docling's full
    provenance tree, which would bloat every vector payload."""

    def extract_chunk_meta(self, file_path: str, chunk: Any) -> dict[str, Any]:
        items = getattr(chunk.meta, "doc_items", []) or []
        labels = {getattr(item.label, "value", str(item.label)) for item in items}
        pages = sorted({p.page_no for item in items for p in (item.prov or [])})
        if "table" in labels:
            modality = Modality.TABLE
        elif labels & {"picture", "chart"}:
            modality = Modality.IMAGE
        else:
            modality = Modality.TEXT
        headings = getattr(chunk.meta, "headings", None) or []
        is_reference = (bool(labels) and labels <= {"reference"}) or any(
            NON_CONTENT_HEADING.match(h) for h in headings
        )
        return {
            "section": " > ".join(headings) or None,
            "page": pages[0] if pages else None,
            "modality": modality.value,
            "is_reference": is_reference,
        }

    def extract_dl_doc_meta(self, file_path: str, dl_doc: Any) -> dict[str, Any]:
        return {}


@lru_cache
def _converter() -> DocumentConverter:
    figures = picture_description_options()
    options = PdfPipelineOptions(
        do_ocr=False,
        do_table_structure=True,
        table_structure_options=TableStructureOptions(mode=TableFormerMode.FAST),
        do_picture_description=figures is not None,
        enable_remote_services=figures is not None,  # Docling's opt-in for remote API calls
        generate_picture_images=figures is not None,
        images_scale=2.0,  # sharper figure crops so the vision model can read labels
    )
    if figures is not None:
        options.picture_description_options = figures
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )


@lru_cache
def _chunker() -> HybridChunker:
    tokenizer = HuggingFaceTokenizer.from_pretrained(
        get_settings().embedding_model, max_tokens=CHUNK_MAX_TOKENS
    )
    return HybridChunker(tokenizer=tokenizer, merge_peers=True)


def parse_pdf(path: Path) -> list[Document]:
    ensure_vision_reachable(picture_description_options())
    loader = DoclingLoader(
        file_path=str(path),
        converter=_converter(),
        chunker=_chunker(),
        export_type=ExportType.DOC_CHUNKS,
        meta_extractor=CompactMetaExtractor(),
    )
    chunks = loader.load()
    kept = [c for c in chunks if not c.metadata.pop("is_reference", False)]
    return kept
