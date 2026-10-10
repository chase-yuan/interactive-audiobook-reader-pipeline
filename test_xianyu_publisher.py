"""Unit tests for xianyu_publisher module."""

import unittest
from pathlib import Path
from xianyu_publisher import (
    resolve_book_metadata,
    generate_marketing_copy,
    CANONICAL_CHINESE_TITLES,
    THEMATIC_HOOKS,
)


class TestXianyuPublisher(unittest.TestCase):
    def test_canonical_titles_and_hooks_exist(self):
        self.assertIn("beyond-feelings", CANONICAL_CHINESE_TITLES)
        self.assertEqual(CANONICAL_CHINESE_TITLES["beyond-feelings"], "超越感觉")
        self.assertIn("beyond-feelings", THEMATIC_HOOKS)

    def test_resolve_book_metadata_beyond_feelings(self):
        meta = resolve_book_metadata("beyond-feelings")
        self.assertEqual(meta["id"], "beyond-feelings")
        self.assertEqual(meta["title_cn"], "超越感觉")
        self.assertIn("Beyond Feelings", meta["title_en"])
        self.assertTrue(Path(meta["cover_path"]).is_file())
        self.assertIn("https://audiblelibrary.online/books/beyond-feelings/", meta["url"])

    def test_marketing_copy_contract(self):
        meta = {
            "id": "beyond-feelings",
            "title_cn": "超越感觉",
            "title_en": "Beyond Feelings",
            "subtitle": "批判性思考指南",
            "hook": "走出感觉与主观偏见，建立真正严密、独立的批判性思考逻辑框架。",
            "url": "https://audiblelibrary.online/books/beyond-feelings/",
        }
        tmp_dir = Path("/tmp/test_xianyu_copy_out")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        try:
            detail = generate_marketing_copy(meta, tmp_dir)

            # Contract Invariants: Zero Baidu Netdisk / Zero MP3 download baggage
            self.assertNotIn("百度网盘备份", detail)
            self.assertNotIn("MP3 完整章节", detail)
            self.assertNotIn("EPUB 原版精排电子书", detail)

            # High-conversion value propositions present
            self.assertIn("视听双轨协同", detail)
            self.assertIn("必要难度", detail)
            self.assertIn("单词动态跳动", detail)
            self.assertIn("专属激活卡密", detail)
            self.assertIn("浏览器即开即读", detail)

            # Verify files emitted
            self.assertTrue((tmp_dir / "beyond-feelings_Marketing_Copy.md").is_file())
            self.assertTrue((tmp_dir / "README.md").is_file())

            # Verify SEO titles limit <= 30 chars
            copy_text = (tmp_dir / "README.md").read_text(encoding="utf-8")
            title_section = copy_text.split("## 闲鱼发布标题")[1].split("## 宝贝详情描述")[0]
            for line in title_section.splitlines():
                line = line.strip()
                if line.startswith("1. ") or line.startswith("2. ") or line.startswith("3. "):
                    title_text = line[3:].strip()
                    self.assertLessEqual(
                        len(title_text), 30,
                        f"Title '{title_text}' exceeds Xianyu 30-char limit ({len(title_text)})"
                    )
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
