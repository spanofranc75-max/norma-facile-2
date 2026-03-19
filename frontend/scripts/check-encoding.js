#!/usr/bin/env node
/**
 * check-encoding.js
 * Scans all JS/JSX/TS/TSX files in src/ for UTF-8 mojibake patterns.
 *
 * Mojibake occurs when UTF-8 bytes are mis-interpreted as Latin-1 and
 * re-saved as UTF-8, producing sequences like:
 *   "ValiditÃÂÃÂ " instead of "Validità"
 *   "EXC1 ÃÂ¢ÃÂÃÂ Strutture" instead of "EXC1 — Strutture"
 *
 * Usage:
 *   node scripts/check-encoding.js          — check only (exit 1 if issues)
 *   node scripts/check-encoding.js --fix    — auto-fix using Python ftfy
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const SRC_DIR = path.join(__dirname, '..', 'src');
const EXTENSIONS = new Set(['.js', '.jsx', '.ts', '.tsx']);

// Mojibake fingerprints: these byte sequences should never appear in clean UTF-8 JS source
// They represent multi-level re-encodings of common Unicode characters (Italian accents, em-dash, etc.)
const MOJIBAKE_PATTERNS = [
  // Triple-encoded 2-byte Latin chars (à, è, é, ì, ò, ù → Ã\x83Â...)
  /\xc3\x83\xc2\x83/,
  // Double-encoded em-dash / similar 3-byte chars (— → Ã¢Â\x80...)
  /\xc3\xa2\xc2\x80/,
  // Generic: lone Ã followed by non-standard continuation (double-encoded 2-byte seqs)
  /\xc3[\x80-\x9f]/,
];

function scanFile(filePath) {
  const buf = fs.readFileSync(filePath);
  const issues = [];
  MOJIBAKE_PATTERNS.forEach((pattern, i) => {
    if (pattern.test(buf)) {
      issues.push(`pattern-${i}: ${pattern}`);
    }
  });
  return issues;
}

function walkDir(dir) {
  const results = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory() && entry.name !== 'node_modules' && !entry.name.startsWith('.')) {
      results.push(...walkDir(full));
    } else if (entry.isFile() && EXTENSIONS.has(path.extname(entry.name))) {
      results.push(full);
    }
  }
  return results;
}

const autoFix = process.argv.includes('--fix');
const files = walkDir(SRC_DIR);
const affected = [];

for (const file of files) {
  const issues = scanFile(file);
  if (issues.length > 0) {
    affected.push({ file, issues });
    console.error(`[ENCODING ERROR] ${path.relative(process.cwd(), file)}`);
    issues.forEach(i => console.error(`  → ${i}`));
  }
}

if (affected.length === 0) {
  console.log('[ENCODING OK] No mojibake found in', files.length, 'files.');
  process.exit(0);
}

console.error(`\n[ENCODING] ${affected.length} file(s) with encoding issues.`);

if (autoFix) {
  console.log('[ENCODING] Attempting auto-fix with ftfy...');
  try {
    const filePaths = affected.map(a => `"${a.file}"`).join(' ');
    execSync(
      `python3 -c "
import ftfy, sys
for fp in sys.argv[1:]:
    with open(fp, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    fixed = ftfy.fix_text(content)
    if content != fixed:
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(fixed)
        print('Fixed:', fp)
    else:
        print('No change:', fp)
" ${filePaths}`,
      { stdio: 'inherit' }
    );
    console.log('[ENCODING] Auto-fix complete. Run check again to verify.');
    process.exit(0);
  } catch (err) {
    console.error('[ENCODING] Auto-fix failed:', err.message);
    console.error('Install ftfy: pip install ftfy');
    process.exit(1);
  }
}

console.error('\nRun with --fix to auto-repair: yarn check:encoding --fix');
process.exit(1);
