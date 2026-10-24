"""
Module: extract_epub.py
Description: Unabridged 1-Sentence-1-Card EPUB Sentence Extractor with abbreviation and parenthetical protection.
"""

import zipfile
import re
import json
from pathlib import PurePosixPath
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
    BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "div", "tr", "th", "td"}

    def __init__(self):
        super().__init__()
        self.elements = []
        self.stack = []  # list of (tag, attrs_dict, text_chunks)
        self.ignored_tags = []
        self.table_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class", "").lower()
        elem_id = attrs_dict.get("id", "").lower()
        epub_type = attrs_dict.get("epub:type", "").lower()

        if tag in ("table", "thead", "tbody", "tfoot"):
            self.table_depth += 1

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
                    p_cls = parent_attrs.get("class", "").lower()
                    is_tab = self.table_depth > 0 or parent_tag in ("table", "tr", "th", "td") or any(w in p_cls for w in ["table", "tabular"])
                    self.elements.append({
                        "tag": parent_tag,
                        "class": parent_attrs.get("class", ""),
                        "text": re.sub(r"\s+", " ", text),
                        "is_tabular": is_tab,
                    })
                self.stack[-1][2].clear()

            self.stack.append((tag, attrs_dict, []))

    def handle_endtag(self, tag):
        if tag in ("table", "thead", "tbody", "tfoot"):
            self.table_depth = max(0, self.table_depth - 1)

        if self.ignored_tags:
            if tag == self.ignored_tags[-1]:
                self.ignored_tags.pop()
            return

        if self.stack and tag == self.stack[-1][0]:
            popped_tag, popped_attrs, text_chunks = self.stack.pop()
            text = "".join(text_chunks).strip()
            if text:
                p_cls = popped_attrs.get("class", "").lower()
                is_tab = self.table_depth > 0 or popped_tag in ("table", "tr", "th", "td") or any(w in p_cls for w in ["table", "tabular"])
                self.elements.append({
                    "tag": popped_tag,
                    "class": popped_attrs.get("class", ""),
                    "text": re.sub(r"\s+", " ", text),
                    "is_tabular": is_tab,
                })

    def handle_data(self, data):
        if self.stack and not self.ignored_tags:
            self.stack[-1][2].append(data)


def is_title_text(txt: str) -> bool:
    if not txt:
        return False
    words = [w for w in re.findall(r"[a-zA-Z0-9'’]+", txt)]
    if not words or len(words) > 12:
        return False
    if re.search(r"[.!?…]$", txt.strip()):
        return False
    if txt.startswith(("Part ", "Chapter ", "Section ", "Appendix ", "Preface ", "Introduction ", "Book ", "Prologue", "Epilogue", "Table ", "Figure ")):
        return True
    minor_words = {"a", "an", "the", "and", "but", "or", "for", "nor", "on", "in", "at", "to", "from", "by", "with", "of", "off", "out", "as", "into", "over", "up", "down"}
    cap_count = 0
    significant_count = 0
    for w in words:
        if w.lower() in minor_words:
            continue
        significant_count += 1
        if w[0].isupper():
            cap_count += 1
    if significant_count > 0 and cap_count == significant_count:
        return True
    if txt.isupper():
        return True
    return False


def is_heading_element(el: dict) -> bool:
    tag = el.get("tag", "").lower()
    if tag.startswith("h") and len(tag) <= 2 and tag[1:].isdigit():
        return True
    cls = el.get("class", "").lower()
    classes = set(cls.split())
    heading_markers = {"h", "h1", "h2", "h3", "h4", "h5", "h6", "cn", "fm-co1", "title", "chapter-title", "heading", "subheading", "calibre_12"}
    txt = el.get("text", "").strip()
    is_short = len(txt.split()) <= 15 and not re.search(r"[.!?…].*[.!?…]", txt)
    if is_short and (classes & heading_markers or cls in heading_markers):
        return True
    return is_title_text(txt)


def clean_and_merge_elements(elements):
    """
    Clean and merge adjacent block elements:
    1. Reconnect words broken by trailing hyphens across elements:
       e.g. '...oversimplifi-' + 'cation...' -> '...oversimplification...'
    2. Merge lines that do not end with terminal punctuation ([.!?…”"’)]):
       soft line wraps in print editions.
    3. Drop duplicate consecutive identical headers/footers.
    """
    if not elements:
        return []

    # Step 1: Filter out duplicate consecutive identical text (running headers/footers)
    deduped = []
    prev_txt = None
    for el in elements:
        txt = el.get("text", "").strip()
        if not txt:
            continue
        if txt == prev_txt and len(txt) < 100:
            continue
        deduped.append(dict(el))
        prev_txt = txt

    if not deduped:
        return []

    # Step 2: Merge elements
    merged = []
    curr = deduped[0]

    for next_el in deduped[1:]:
        curr_tag = curr.get("tag", "p")
        next_tag = next_el.get("tag", "p")
        curr_txt = curr.get("text", "").strip()
        next_txt = next_el.get("text", "").strip()

        is_curr_heading = is_heading_element(curr)
        is_next_heading = is_heading_element(next_el)

        # Never merge headings with non-headings, or headings with other headings
        if is_curr_heading or is_next_heading:
            merged.append(curr)
            curr = next_el
            continue

        # Never merge tabular elements with non-tabular prose
        if bool(curr.get("is_tabular")) != bool(next_el.get("is_tabular")):
            merged.append(curr)
            curr = next_el
            continue

        # Case A: Trailing hyphen at the end of curr_txt: e.g. "oversimplifi-"
        if re.search(r"\b[a-zA-Z]+-\s*$", curr_txt):
            base = re.sub(r"-\s*$", "", curr_txt)
            curr["text"] = base + next_txt
            continue

        # Case B: next_txt starts with lowercase (unmerged sentence continuation)
        next_starts_lower = bool(re.match(r"^\s*[\"“‘'(\[]*[a-z]", next_txt))

        # Case C: Check if curr_txt is a title or header
        is_title = is_title_text(curr_txt)

        curr_has_terminal = bool(re.search(r"[.!?…”\"’)]$", curr_txt))

        # Hard ceiling on soft-wrap merges to prevent mega-sentence bloat in unpunctuated lists/tables
        is_too_long = len(curr_txt.split()) >= 40 or len(curr_txt) >= 280

        if (next_starts_lower or (not curr_has_terminal and not is_title)) and not is_too_long:
            curr["text"] = curr_txt + " " + next_txt
        else:
            merged.append(curr)
            curr = next_el

    merged.append(curr)
    return merged


def extract_chapter_from_epub(epub_path, chapter_internal_path, out_json_path):
    if isinstance(chapter_internal_path, (list, tuple)):
        href_specs = list(chapter_internal_path)
    else:
        href_specs = [chapter_internal_path]

    for spec in href_specs:
        h = spec["href"] if isinstance(spec, dict) else (spec.split("::")[0] if isinstance(spec, str) and "::" in spec else spec)
        pure = PurePosixPath(h)
        if pure.is_absolute() or ".." in pure.parts:
            raise ValueError(f"Insecure chapter internal path: {h}")

    canonical_items = []
    s_idx = 0
    global_elem_idx = 0
    with zipfile.ZipFile(epub_path, 'r') as z:
        for spec in href_specs:
            if isinstance(spec, dict):
                h = spec["href"]
                start_marker = spec.get("start")
                stop_marker = spec.get("stop")
            elif isinstance(spec, str) and "::" in spec:
                parts = spec.split("::")
                h = parts[0]
                start_marker = None
                stop_marker = None
                for param in parts[1:]:
                    if param.startswith("start="):
                        start_marker = param[6:]
                    elif param.startswith("stop="):
                        stop_marker = param[5:]
            else:
                h = spec
                start_marker = None
                stop_marker = None

            raw_html = z.read(h).decode('utf-8')
            parser = ChapterParser()
            parser.feed(raw_html)
            cleaned_elements = clean_and_merge_elements(parser.elements)

            def _matches_marker(marker_str, element):
                if not marker_str:
                    return False
                m_clean = marker_str.strip().lower()
                el_txt = element.get('text', '').strip().lower()
                pattern = rf"(?<![a-z0-9]){re.escape(m_clean)}(?![a-z0-9])"
                if not re.search(pattern, el_txt):
                    return False
                # If marker is short (<= 3 words), prevent casual substring collisions in body text
                if len(m_clean.split()) <= 3:
                    return is_heading_element(element) or len(el_txt.split()) <= 25
                return True

            active = (start_marker is None)
            for el in cleaned_elements:
                tag = el['tag']
                txt = el['text']
                cls = el.get('class', '').lower()

                if not active and start_marker and _matches_marker(start_marker, el):
                    active = True
                elif active and stop_marker and _matches_marker(stop_marker, el):
                    break
                if not active:
                    continue

                is_h = is_heading_element(el)
                
                is_tabular = bool(el.get("is_tabular")) or bool(re.search(r"Click (?:here )?for a larger image of this (?:table|chart|figure)", txt, re.IGNORECASE))
                if is_h:
                    canonical_items.append({
                        "id": f"s-{s_idx}",
                        "elem_idx": global_elem_idx,
                        "tag": tag,
                        "text": txt,
                        "is_heading": True,
                        "is_tabular": is_tabular
                    })
                    s_idx += 1
                    global_elem_idx += 1
                else:
                    sents = split_into_atomic_sentences(txt)
                    for s in sents:
                        canonical_items.append({
                            "id": f"s-{s_idx}",
                            "elem_idx": global_elem_idx,
                            "tag": tag,
                            "text": s,
                            "is_heading": False,
                            "is_tabular": is_tabular
                        })
                        s_idx += 1
                    global_elem_idx += 1
                
    atomic_write_json(out_json_path, canonical_items)
        
    print(f"Extracted {len(canonical_items)} canonical sentences from {chapter_internal_path} -> {out_json_path}")
    return canonical_items

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 4:
        extract_chapter_from_epub(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Usage: python3 extract_epub.py <epub_path> <chapter_internal_path> <out_json_path>")
