import { mkdirSync, readdirSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export function galleryItems(value: string) {
  return value.split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
}

function folderFor(slug: string) {
  if (!SLUG.test(slug)) throw new Error('This college address is not valid.');
  const here = fileURLToPath(new URL('.', import.meta.url));
  return join(here, '..', '..', 'public', 'media', 'colleges', slug);
}

function kind(bytes: Buffer) {
  if (bytes[0] === 0xff && bytes[1] === 0xd8) return '.jpg';
  if (bytes[0] === 0x89 && bytes[1] === 0x50) return '.png';
  if (bytes.subarray(0, 4).toString() === 'RIFF' && bytes.subarray(8, 12).toString() === 'WEBP') return '.webp';
  if (bytes.subarray(0, 4).toString() === 'GIF8') return '.gif';
  throw new Error('Use a JPG, PNG, WEBP, or GIF.');
}

export function saveNamed(slug: string, name: string, bytes: Buffer) {
  if (!/^[a-z0-9-]+$/.test(name)) throw new Error('This photo could not be saved.');
  const ext = kind(bytes);
  const folder = folderFor(slug);
  mkdirSync(folder, { recursive: true });
  for (const file of readdirSync(folder)) {
    if (file.startsWith(`${name}.`)) rmSync(join(folder, file));
  }
  writeFileSync(join(folder, `${name}${ext}`), bytes);
}

export function removeNamed(slug: string, name: string) {
  const folder = folderFor(slug);
  let files: string[] = [];
  try {
    files = readdirSync(folder);
  } catch {
    return;
  }
  for (const file of files) {
    if (file.startsWith(`${name}.`)) rmSync(join(folder, file));
  }
}

export function normalizeGallery(slug: string, items: string[]) {
  const folder = folderFor(slug);
  mkdirSync(folder, { recursive: true });
  const held: string[] = [];
  for (const file of readdirSync(folder)) {
    if (file.endsWith('.part')) continue;
    if (file.startsWith('gallery-') || file.startsWith('incoming-')) {
      const next = `hold-${file}`;
      renameSync(join(folder, file), join(folder, next));
      held.push(next);
    }
  }
  const saved: string[] = [];
  for (const item of items) {
    if (item.startsWith('https://')) {
      saved.push(item);
      continue;
    }
    const marker = item.split('/').pop() || '';
    const hold = held.find((file) => file.startsWith(`hold-${marker}.`));
    if (!hold) continue;
    const ext = hold.slice(hold.lastIndexOf('.'));
    const position = saved.length + 1;
    renameSync(join(folder, hold), join(folder, `gallery-${position}${ext}`));
    held.splice(held.indexOf(hold), 1);
    saved.push(`/media/colleges/${slug}/gallery-${position}`);
  }
  for (const file of held) rmSync(join(folder, file));
  return saved;
}

export function photoState(
  slug: string,
  college: { imageUrl: string; imagePath: string; logoUrl: string; logoPath: string; gallery: string },
) {
  const version = Date.now();
  const one = (path: string, url: string, name: string) => (
    path.startsWith('/media/') || url.startsWith('https://') ? `/media/colleges/${slug}/${name}?v=${version}` : ''
  );
  return {
    hero: one(college.imagePath, college.imageUrl, 'hero'),
    logo: one(college.logoPath, college.logoUrl, 'logo'),
    gallery: galleryItems(college.gallery).map((item, index) => (
      item.startsWith('/media/') ? `${item}?v=${version}` : `/media/colleges/${slug}/gallery-${index + 1}?v=${version}`
    )),
  };
}
