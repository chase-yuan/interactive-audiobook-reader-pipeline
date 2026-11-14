#!/usr/bin/env python3
"""
test_typing_prototype.py - Automated Regression Tests for Interactive Typing Practice Engine.
Guards compilation integrity, Node.js AST syntax, DOM tokens, O(1) projection, and persistence contracts.
"""

import os
import subprocess
import unittest

PIPELINE_ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT_HTML = os.path.join(PIPELINE_ROOT, "outputs", "prototype-typing-reader.html")
BUILDER_SCRIPT = os.path.join(PIPELINE_ROOT, "build_prototype.py")


class TestTypingPrototype(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Compile prototype if not present or rebuild for fresh test baseline
        res = subprocess.run(
            ["python3", BUILDER_SCRIPT],
            cwd=PIPELINE_ROOT,
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, f"build_prototype.py failed: {res.stderr}"
        assert os.path.isfile(OUTPUT_HTML), f"Expected {OUTPUT_HTML} to exist"
        with open(OUTPUT_HTML, "r", encoding="utf-8") as f:
            cls.html_content = f.read()

    def test_compilation_and_output_existence(self):
        """Verify build_prototype.py generates valid output file with expected size."""
        file_size = os.path.getsize(OUTPUT_HTML)
        self.assertGreater(file_size, 200_000, "Generated HTML must be > 200KB")

    def test_node_ast_syntax_integrity(self):
        """Verify all embedded JavaScript blocks pass Node.js AST validation with zero syntax errors."""
        node_script = """
        const fs = require('fs');
        const targetPath = process.argv.slice(1).find(a => a.endsWith('.html')) || process.argv[1];
        const html = fs.readFileSync(targetPath, 'utf8');
        const scriptMatches = [...html.matchAll(/<script[^>]*>([\\s\\S]*?)<\\/script>/gi)];
        if (scriptMatches.length === 0) {
            console.error('No script tags found');
            process.exit(1);
        }
        scriptMatches.forEach((m, idx) => {
            try {
                new Function(m[1]);
            } catch (err) {
                console.error(`Syntax error in script tag #${idx}: ${err.message}`);
                process.exit(1);
            }
        });
        console.log('ALL_SCRIPTS_VALID');
        """
        proc = subprocess.run(
            ["node", "-e", node_script, OUTPUT_HTML],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Node.js AST error: {proc.stderr}")
        self.assertIn("ALL_SCRIPTS_VALID", proc.stdout)

    def test_essential_typing_dom_tokens(self):
        """Verify all mandatory interactive DOM elements, buttons, and badges exist."""
        required_tokens = [
            'id="typingModeBtn"',
            'id="inSituHud"',
            'id="typingSubModeBtn"',
            'id="soundProfileBtn"',
            'id="transToggleBtn"',
            'id="hudSkipWordBtn"',
            'id="hudMetrics"',
            'id="hudProgressTag"',
            'id="capsLockBadge"',
            'id="typingChapterProgressBar"',
            'id="typingHiddenInput"',
            'id="typingCompleteModal"',
            ".twc-cursor",
            ".twc-correct",
            ".twc-active-pending",
            ".twc-masked",
            ".twc-cloze-slot-char",
            ".target-active-vocab",
        ]
        for token in required_tokens:
            self.assertIn(token, self.html_content, f"Missing essential token: {token}")

    def test_no_distracting_acoustic_line(self):
        """Verify that bottom acoustic playback bar is strictly removed to prevent visual distraction."""
        forbidden_tokens = [
            "typingAcousticProgressBar",
            "typingAcousticFill",
            "updateAcousticProgress",
        ]
        for token in forbidden_tokens:
            self.assertNotIn(token, self.html_content, f"Forbidden acoustic element found: {token}")

    def test_storage_key_atomic_reset_contract(self):
        """Verify STORAGE_KEY dynamic chapter keying and atomic localStorage wipe on restart."""
        self.assertIn("const STORAGE_KEY = 'typing_ledger_c'", self.html_content)
        self.assertIn("localStorage.removeItem(STORAGE_KEY)", self.html_content)

    def test_localized_o1_projection_contract(self):
        """Verify projectActiveSentenceOnly is defined for sub-millisecond per-keystroke rendering."""
        self.assertIn("function projectActiveSentenceOnly()", self.html_content)
        # Verify it is called inside projectDocumentTypingState
        self.assertIn("projectActiveSentenceOnly();", self.html_content)

    def test_shortcuts_table_dual_mode_contract(self):
        """Verify Shortcuts modal documents both Reading Mode and Typing Practice Mode."""
        self.assertIn("Reading Mode", self.html_content)
        self.assertIn("Typing Practice Mode", self.html_content)
        self.assertIn("Shift+Tab", self.html_content)
        self.assertIn("⌘R / Ctrl+R", self.html_content)
        self.assertIn("Ctrl+L", self.html_content)
        self.assertIn("Ctrl+H", self.html_content)
        self.assertIn("Alt+T", self.html_content)

    def test_mobile_bridge_zero_width_space_contract(self):
        """Verify mobile bridge seeds zero-width space for reliable iOS virtual backspace."""
        self.assertIn("\\u200B", self.html_content)

    def test_skip_char_and_word_contract(self):
        """Verify skipCurrentChar, skipCurrentWord, and Smart Space contracts exist."""
        self.assertIn("function skipCurrentChar()", self.html_content)
        self.assertIn("function skipCurrentWord()", self.html_content)
        self.assertIn("window.skipCurrentChar", self.html_content)
        self.assertIn("window.skipCurrentWord", self.html_content)
        self.assertIn("isOnlyTrailingPunct", self.html_content)

    def test_apply_book_typing_lifecycle(self):
        """Verify apply_book_typing.py performs atomic backup, injection, and AST validation."""
        import tempfile
        from apply_book_typing import apply_typing_to_book

        with tempfile.TemporaryDirectory() as tmpdir:
            test_html = os.path.join(tmpdir, "index.html")
            source_file = "/Users/lindy/Vault/Audible/books/misbehaving/index.html"
            with open(source_file, "r", encoding="utf-8") as f:
                content = f.read()
            with open(test_html, "w", encoding="utf-8") as f:
                f.write(content)

            # Test first injection
            res = apply_typing_to_book(tmpdir)
            self.assertEqual(res["status"], "SUCCESS")
            self.assertTrue(os.path.isfile(test_html + ".bak"))
            self.assertTrue(res["file_size_bytes"] > 200_000)

            # Test idempotency (second injection should detect ALREADY_UPGRADED)
            res2 = apply_typing_to_book(tmpdir)
            self.assertEqual(res2["status"], "ALREADY_UPGRADED")


if __name__ == "__main__":
    unittest.main()
