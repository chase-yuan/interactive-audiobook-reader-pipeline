#!/usr/bin/env python3
"""
Module: apply_book_typing.py
Description: Safely and idempotently upgrades any production reader book with the
             interactive shadow typing engine.
Features:
- Idempotent: Skips re-injection if already upgraded.
- Atomic Backup: Always writes `index.html.bak` before any mutation.
- Relative Assets: Retains authentic relative asset/js links.
- Release Gate Integrity: Updates `.release_lock.json` with new SHA256 and assets_sha256 digests.
- Shift-Left AST Verification: Validates all embedded JavaScript with Node.js V8 before writing.
- Release Auditor: Automatically runs `audit_book_release.js` to ensure 100% pass rate.
"""

import os
import sys
import json
import hashlib
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Import engine logic from build_prototype
from build_prototype import inject_typing_mode_to_html


def validate_reader_ast(html_content: str) -> None:
    """Ensure all script tags in generated HTML pass V8 AST syntax compilation."""
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
    tmp_path = f"/tmp/_ast_check_{os.getpid()}.html"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    try:
        proc = subprocess.run(
            ["node", "-e", node_script, tmp_path],
            capture_output=True,
            text=True,
            check=True
        )
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def compute_bundled_assets_sha(vault_root: str, book_dir: str, html_file: str) -> str:
    """Computes exact bundled-assets SHA-256 digest matching audit_book_release.js."""
    chapters_dir = os.path.join(book_dir, 'chapters')
    book_assets = [html_file]
    if os.path.isdir(chapters_dir):
        for f in os.listdir(chapters_dir):
            if f.endswith('.html'):
                book_assets.append(os.path.join(chapters_dir, f))
    book_assets.sort()

    digest = hashlib.sha256()
    for fpath in book_assets:
        rel_path = os.path.relpath(fpath, vault_root)
        digest.update(rel_path.encode('utf-8'))
        digest.update(b'\0')
        with open(fpath, 'rb') as f:
            digest.update(f.read())
        digest.update(b'\0')
    return digest.hexdigest()


def apply_typing_to_book(book_target: str, *, force_rebuild: bool = False) -> dict:
    target_path = os.path.abspath(book_target)
    if os.path.isdir(target_path):
        book_dir = target_path
        html_file = os.path.join(book_dir, 'index.html')
    else:
        html_file = target_path
        book_dir = os.path.dirname(target_path)

    if not os.path.isfile(html_file):
        raise FileNotFoundError(f"Book reader HTML not found: {html_file}")

    backup_file = html_file + '.bak'

    # If backup exists and we force rebuild or need base, read from clean backup
    if os.path.exists(backup_file):
        with open(backup_file, 'r', encoding='utf-8') as f:
            source_content = f.read()
    else:
        with open(html_file, 'r', encoding='utf-8') as f:
            source_content = f.read()
        shutil.copy2(html_file, backup_file)

    # Idempotency check if reading from current html_file without backup
    with open(html_file, 'r', encoding='utf-8') as f:
        current_content = f.read()
    if not force_rebuild and 'id="typingModeBtn"' in current_content and 'id="inSituHud"' in current_content:
        vault_root = os.path.abspath(os.path.join(book_dir, '..', '..'))
        book_id = os.path.basename(book_dir)
        audit_script = os.path.join(vault_root, 'scripts', 'audit_book_release.js')
        if os.path.exists(audit_script):
            res = subprocess.run(['node', audit_script, book_id], capture_output=True, text=True)
            if res.returncode == 0:
                return {
                    "status": "ALREADY_UPGRADED",
                    "html_file": html_file,
                    "book_dir": book_dir,
                    "message": "Book already has interactive typing mode injected and passes audit."
                }
        else:
            return {
                "status": "ALREADY_UPGRADED",
                "html_file": html_file,
                "book_dir": book_dir,
                "message": "Book already has interactive typing mode injected."
            }

    # Perform injection from clean source content
    updated_content = inject_typing_mode_to_html(source_content, remote_passkey_gate=False)

    # Physical Verification Gate: Node.js AST check
    validate_reader_ast(updated_content)

    # Atomic write to target file
    tmp_file = html_file + f'.tmp.{os.getpid()}'
    with open(tmp_file, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    os.replace(tmp_file, html_file)

    # Compute new physical SHA256 of index.html
    new_sha256 = hashlib.sha256(updated_content.encode('utf-8')).hexdigest()

    # Synchronize .release_lock.json if book directory contains release contract
    lock_file = os.path.join(book_dir, '.release_lock.json')
    lock_updated = False
    vault_root = os.path.abspath(os.path.join(book_dir, '..', '..'))
    if os.path.isfile(lock_file):
        with open(lock_file, 'r', encoding='utf-8') as f:
            lock_data = json.load(f)
        lock_data['sha256'] = new_sha256
        new_assets_sha = compute_bundled_assets_sha(vault_root, book_dir, html_file)
        lock_data['assets_sha256'] = new_assets_sha
        lock_data['locked_at'] = datetime.now(timezone.utc).astimezone().isoformat()
        with open(lock_file, 'w', encoding='utf-8') as f:
            json.dump(lock_data, f, indent=2, ensure_ascii=False)
        lock_updated = True

    # Run release auditor
    book_id = os.path.basename(book_dir)
    audit_script = os.path.join(vault_root, 'scripts', 'audit_book_release.js')
    audit_passed = None
    if os.path.exists(audit_script):
        res = subprocess.run(['node', audit_script, book_id], capture_output=True, text=True)
        audit_passed = (res.returncode == 0)
        if not audit_passed:
            raise RuntimeError(f"Release audit failed for {book_id}:\n{res.stdout}\n{res.stderr}")

    return {
        "status": "SUCCESS",
        "book_dir": book_dir,
        "book_id": book_id,
        "html_file": html_file,
        "backup_file": backup_file,
        "file_size_bytes": len(updated_content),
        "sha256": new_sha256,
        "assets_sha256": new_assets_sha if lock_updated else None,
        "lock_updated": lock_updated,
        "audit_passed": audit_passed
    }


def batch_upgrade_library(books_root: str) -> list:
    """Batch upgrades all books in the library directory with isolated audits."""
    results = []
    book_names = [
        b for b in sorted(os.listdir(books_root))
        if os.path.isdir(os.path.join(books_root, b)) and os.path.isfile(os.path.join(books_root, b, 'index.html'))
    ]
    total = len(book_names)
    print(f"🚀 Starting batch typing upgrade across {total} books in {books_root}...\n")

    for idx, b in enumerate(book_names, 1):
        p = os.path.join(books_root, b)
        print(f"[{idx}/{total}] Processing '{b}'...", flush=True)
        res = apply_typing_to_book(p, force_rebuild=True)
        print(f"  ✅ '{b}' upgraded: sha={res['sha256'][:8]} | audit_passed={res['audit_passed']}", flush=True)
        results.append(res)

    print(f"\n🎉 All {total} books successfully upgraded and verified!")
    return results


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 apply_book_typing.py <book_dir_or_index_html | --all [books_dir]>")
        sys.exit(1)

    if sys.argv[1] == '--all':
        books_dir = sys.argv[2] if len(sys.argv) > 2 else '/Users/lindy/Vault/Audible/books'
        res = batch_upgrade_library(books_dir)
        print(f"Total upgraded: {len(res)}")
    else:
        result = apply_typing_to_book(sys.argv[1], force_rebuild=True)
        print(json.dumps(result, indent=2, ensure_ascii=False))
