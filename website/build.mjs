import fs from 'node:fs/promises';
import path from 'node:path';
import { marked, Marked } from 'marked';
const root = path.resolve(import.meta.dirname, '..');
const dist = path.join(root, 'website/dist');
await fs.rm(dist, { recursive: true, force: true });
await fs.mkdir(dist, { recursive: true });
const books = [];
const writings = [];
// The reader supports code fences; remove raw HTML at the token level.
const writingMarkdown = new Marked({ renderer: { html() { return ''; } } });
const writingRoot = path.join(root, 'writings');
for (const dir of await fs.readdir(writingRoot, { withFileTypes: true }).catch(error => {
  if (error.code === 'ENOENT') return [];
  throw error;
})) {
  if (!dir.isDirectory()) continue;
  const base = path.join(writingRoot, dir.name);
  const meta = JSON.parse(await fs.readFile(path.join(base, 'work.json'), 'utf8'));
  const assetDir = path.join(dist, 'writings', meta.id);
  await fs.mkdir(assetDir, { recursive: true });
  if (await fs.stat(path.join(base, 'assets')).catch(() => null))
    await fs.cp(path.join(base, 'assets'), path.join(assetDir, 'assets'), { recursive: true });
  const chapters = [];
  for (const chapter of meta.chapters || []) {
    if (!chapter.file) continue;
    const raw = await fs.readFile(path.join(base, chapter.file), 'utf8');
    const md = raw.replace(/^---\n[\s\S]*?\n---\n/, '');
    const chunks = md.split(/<!-- block: ([\w-]+) -->/);
    const blocks = [];
    for (let i = 1; i < chunks.length; i += 2) {
      const source = chunks[i + 1].trim().replace(/\]\(\.\.\/assets\//g, `](writings/${meta.id}/assets/`);
      blocks.push({ id: chunks[i], title: source.match(/^## (.+)/m)?.[1] || chunks[i], html: writingMarkdown.parse(source), text: source.replace(/!\[[^\]]*\]\([^)]*\)/g, '').replace(/[#*`]/g, '') });
    }
    if (!blocks.length) throw Error(`Chapter has no blocks: ${chapter.id}`);
    chapters.push({ id: chapter.id, file: chapter.file, title: chapter.title, label: chapter.label, summary: chapter.summary,
      status: chapter.status, version: chapter.version, material_note: chapter.material_note,
      writing_id: meta.id, number: chapters.length + 1, blocks, image_count: (md.match(/!\[/g) || []).length,
      updated: raw.match(/^updated: (.+)$/m)?.[1] || '', intro: chunks[0].match(/^> (.*)/m)?.[1] || '' });
  }
  writings.push({ id: meta.id, title: meta.title, author: meta.author, kind: meta.kind, description: meta.description,
    status: meta.status, writing_progress: meta.writing_progress, chapters,
    outline: (meta.chapters || []).map(c => ({ id: c.id, title: c.title, status: c.status, available: !!c.file })) });
}
for (const dir of await fs.readdir(path.join(root, 'books'), { withFileTypes: true })) {
  if (!dir.isDirectory()) continue;
  const base = path.join(root, 'books', dir.name);
  const meta = JSON.parse(await fs.readFile(path.join(base, 'book.json'), 'utf8'));
  const assetDir = path.join(dist, 'books', meta.id);
  await fs.mkdir(assetDir, { recursive: true });
  await fs.cp(path.join(base, 'assets'), path.join(assetDir, 'assets'), { recursive: true });
  const notes = [];
  for (const note of meta.notes) {
    const raw = await fs.readFile(path.join(base, note.file), 'utf8');
    const md = raw.replace(/^---\n[\s\S]*?\n---\n/, '');
    const chunks = md.split(/<!-- block: ([\w-]+) -->/);
    const blocks = [];
    for (let i = 1; i < chunks.length; i += 2) {
      const id = chunks[i];
      const source = chunks[i + 1].trim();
      const title = source.match(/^## (.+)/m)?.[1] || id;
      // Raw HTML is not part of the note format. Keep generated pages content-only.
      const clean = source.replace(/<[^>]*>/g, '').replace(/\]\(\.\.\/assets\//g, `](books/${meta.id}/assets/`);
      blocks.push({ id, title, html: marked.parse(clean), text: clean.replace(/!\[[^\]]*\]\([^)]*\)/g, '').replace(/[#*`]/g, '') });
    }
    const updated = raw.match(/^updated: (.+)$/m)?.[1] || '';
    notes.push({ ...note, number: notes.length + 1, image_count: (md.match(/!\[/g) || []).length, updated, blocks, wordCount: md.replace(/\s/g, '').length,
      intro: chunks[0].match(/^> (.*)/m)?.[1] || '' });
  }
  books.push({ id: meta.id, title: meta.title, author: meta.author, description: meta.description, category: meta.category, cover_asset: meta.cover_asset, cover_title: meta.cover_title, cover_alt: meta.cover_alt, reading_progress: meta.reading_progress, parts: meta.parts || [], source_total_pages: meta.source_total_pages, notes });
  for (const file of new Set(notes.map(note => note.pdf_export).filter(Boolean))) {
    await fs.copyFile(path.join(base, 'exports', file), path.join(assetDir, file));
  }
}
await fs.mkdir(path.join(dist, 'assets'), { recursive: true });
// A separately supplied font is optional; clean builds use the system serif stack.
if (process.env.KAMI_FONT_PATH) await fs.copyFile(process.env.KAMI_FONT_PATH, path.join(dist, 'assets/kami.ttf'));
for (const name of ['index.html', 'app.js', 'city.svg']) await fs.copyFile(path.join(root, 'website', name), path.join(dist, name));
let css = await fs.readFile(path.join(root, 'website/style.css'), 'utf8');
if (!process.env.KAMI_FONT_PATH) css = css.replace(/^@font-face\{[^}]+\}\s*/, '');
await fs.writeFile(path.join(dist, 'style.css'), css);
const ids = [...books.flatMap(b => b.notes), ...writings.flatMap(w => w.chapters)].map(n => n.id);
if (new Set(ids).size !== ids.length) throw Error('Duplicate note or chapter ID');
await fs.writeFile(path.join(dist, 'content.json'), JSON.stringify({ books, writings }, null, 2));
console.log(`Built ${books.length} book, ${books.reduce((n,b)=>n+b.notes.length,0)} note → ${dist}`);
console.log(`Built ${writings.length} writing, ${writings.reduce((n,w)=>n+w.chapters.length,0)} chapter`);
