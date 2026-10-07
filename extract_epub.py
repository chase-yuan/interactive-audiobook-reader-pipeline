"""
Module: extract_epub.py
Description: Unabridged 1-Sentence-1-Card EPUB Sentence Extractor with abbreviation and parenthetical protection.
"""

import zipfile
import re
import json
from html.parser import HTMLParser
from artifact_io import atomic_write_json

ABBR_TITLES = [
    "Mr", "Mrs", "Ms", "Dr", "Prof", "Sr", "Jr", "Rev", "Hon", "Gen", "Col", "Maj", "Capt", "Lt", "Sgt", "Cpl", "Pvt",
    "Gov", "Sen", "Rep", "Pres", "Sec", "Amb", "Insp", "Det", "St", "Mt", "Ft", "Mme", "Mlle", "Esq", "Ph.D", "M.D", "B.A", "M.A",
    "Jan", "Feb", "Mar", "Apr", "Aug", "Sept", "Oct", "Nov", "Dec"
]

def split_into_atomic_sentences(text):
    protected = text
    # 1. Protect titles, honorifics, and months with trailing dot
    for title in ABBR_TITLES:
        safe_key = f"__ABBR_{title.replace('.', '_')}__"
        protected = re.sub(rf"\b{re.escape(title)}\.", safe_key, protected)

    # 2. Protect single capital initials (e.g. "J. Elon Haldeman", "W. E. B. Du Bois", "J. K. Rowling")
    protected = re.sub(r"\b([A-Z])\.", r"\1__INITIAL_DOT__", protected)

    # 3. Protect decimal numbers (e.g. 3.14, 10.5)
    protected = re.sub(r"(\d+)\.(\d+)", r"\1__NUM_DOT__\2", protected)

    # 4. Protect common latin and reference shorthand
    protected = re.sub(r"\b(e\.g|i\.e|vs|etc|al|fig|figs|pp|vol|vols|no|nos|ch|sec|ed|eds|ibid|cf|ca)\.", r"__\1_DOT__", protected, flags=re.IGNORECASE)

    # 5. Protect a.m./p.m. ONLY when inside a sentence (not followed by a capital letter / abbreviation placeholder)
    protected = re.sub(r"\b(a\.m|p\.m)\.(?!\s+(?:[\"\'“‘\(]?[A-Z0-9]|__ABBR_))", r"__\1_DOT__", protected, flags=re.IGNORECASE)

    # Split pattern for terminal punctuation + quotes/parens + space + (capital OR abbreviation placeholder)
    pattern = re.compile(r"([.!?]+[\"\'”’\)]*)\s+(?=[\"\'“‘\(]?(?:[A-Z0-9]|__ABBR_))")
    tokens = pattern.split(protected)
    sentences = []

    i = 0
    while i < len(tokens):
        part = tokens[i]
        if i + 1 < len(tokens):
            part += tokens[i + 1]
            i += 2
        else:
            i += 1
        part = part.strip()
        if not part:
            continue

        # Restore titles
        for title in ABBR_TITLES:
            safe_key = f"__ABBR_{title.replace('.', '_')}__"
            part = part.replace(safe_key, f"{title}.")

        part = part.replace("__INITIAL_DOT__", ".")
        part = part.replace("__NUM_DOT__", ".")
        part = re.sub(r"__([a-zA-Z\._]+)_DOT__", lambda m: m.group(1).replace("_", ".") + ".", part)
        sentences.append(part)

    return sentences

class ChapterParser(HTMLParser):
    BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "div"}

    def __init__(self):
        super().__init__()
        self.elements = []
        self.stack = []  # list of (tag, attrs_dict, text_chunks)
        self.ignored_tags = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class", "").lower()
        elem_id = attrs_dict.get("id", "").lower()
        epub_type = attrs_dict.get("epub:type", "").lower()

        if (
            self.ignored_tags
            or tag in ["figure", "figcaption"]
            or any(w in cls for w in ["caption", "photocredit", "photo-credit", "illustr", "pagebreak"])
            or elem_id.startswith("page_")
            or elem_id.startswith("page-")
            or epub_type == "pagebreak"
        ):
            self.ignored_tags.append(tag)
            return

        if tag == "img":
            return

        if tag == "br":
            if self.stack:
                self.stack[-1][2].append(" ")
            return

        if tag in self.BLOCK_TAGS:
            # If we are already inside a block tag and have accumulated text, flush it before nesting subblock
            if self.stack and self.stack[-1][2]:
                text = "".join(self.stack[-1][2]).strip()
                if text:
                    parent_tag, parent_attrs, _ = self.stack[-1]
                    self.elements.append({
                        "tag": parent_tag,
                        "class": parent_attrs.get("class", ""),
                        "text": re.sub(r"\s+", " ", text)
                    })
                self.stack[-1][2].clear()

            self.stack.append((tag, attrs_dict, []))

    def handle_endtag(self, tag):
        if self.ignored_tags:
            if tag == self.ignored_tags[-1]:
                self.ignored_tags.pop()
            return

        if self.stack and tag == self.stack[-1][0]:
            popped_tag, popped_attrs, text_chunks = self.stack.pop()
            text = "".join(text_chunks).strip()
            if text:
                self.elements.append({
                    "tag": popped_tag,
                    "class": popped_attrs.get("class", ""),
                    "text": re.sub(r"\s+", " ", text)
                })

    def handle_data(self, data):
        if self.stack and not self.ignored_tags:
            self.stack[-1][2].append(data)

def extract_chapter_from_epub(epub_path, chapter_internal_path, out_json_path):
    with zipfile.ZipFile(epub_path, 'r') as z:
        raw_html = z.read(chapter_internal_path).decode('utf-8')
        
    parser = ChapterParser()
    parser.feed(raw_html)
    
    canonical_items = []
    s_idx = 0
    for elem_idx, el in enumerate(parser.elements):
        tag = el['tag']
        txt = el['text']
        is_h = tag.startswith('h')
        
        if is_h:
            canonical_items.append({
                "id": f"s-{s_idx}",
                "elem_idx": elem_idx,
                "tag": tag,
                "text": txt,
                "is_heading": True
            })
            s_idx += 1
        else:
            sents = split_into_atomic_sentences(txt)
            for s in sents:
                canonical_items.append({
                    "id": f"s-{s_idx}",
                    "elem_idx": elem_idx,
                    "tag": tag,
                    "text": s,
                    "is_heading": False
                })
                s_idx += 1
                
    atomic_write_json(out_json_path, canonical_items)
        
    print(f"Extracted {len(canonical_items)} canonical sentences from {chapter_internal_path} -> {out_json_path}")
    return canonical_items

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 4:
        extract_chapter_from_epub(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Usage: python3 extract_epub.py <epub_path> <chapter_internal_path> <out_json_path>")
