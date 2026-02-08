#!/usr/bin/env node
// Create a new blog post markdown file in src/posts/
// Usage:
//   node tools/new-post.mjs "Post Title" [--tags "Relationships,Anxiety"] [--date "YYYY-MM-DD"] [--draft]

import fs from 'node:fs';
import path from 'node:path';

function slugify(input) {
  return String(input)
    .toLowerCase()
    .trim()
    .replace(/['’]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
}

function todayISO() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

const args = process.argv.slice(2);
if (!args.length || args[0].startsWith('-')) {
  console.error('Missing title. Example: node tools/new-post.mjs "My Title" --tags "Relationships"');
  process.exit(1);
}

const title = args[0];
let tags = [];
let date = todayISO();
let draft = false;

for (let i = 1; i < args.length; i++) {
  const a = args[i];
  if (a === '--tags') {
    const raw = args[++i] ?? '';
    tags = raw
      .split(',')
      .map(s => s.trim())
      .filter(Boolean);
  } else if (a === '--date') {
    date = args[++i] ?? date;
  } else if (a === '--draft') {
    draft = true;
  }
}

const slug = slugify(title);
const filename = `${date}-${slug}.md`;
const outDir = path.join(process.cwd(), 'src', 'posts');
const outPath = path.join(outDir, filename);

if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });
if (fs.existsSync(outPath)) {
  console.error(`Already exists: ${outPath}`);
  process.exit(1);
}

const fmTags = ['posts', ...tags];
const frontMatter = [
  '---',
  'layout: layouts/base.njk',
  `tags: [${fmTags.map(t => JSON.stringify(t)).join(', ')}]`,
  `title: ${JSON.stringify(title)}`,
  `date: ${date}`,
  ...(draft ? ['draft: true'] : []),
  '---',
  '',
].join('\n');

const body = [
  '<div class="prose">',
  '',
  'Write your post here.',
  '',
  '</div>',
  '',
].join('\n');

fs.writeFileSync(outPath, frontMatter + body, 'utf8');
console.log(`Created: ${outPath}`);
