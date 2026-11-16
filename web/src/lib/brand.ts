import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

export type BrandSlot = 'logo' | 'favicon';

const LIMIT = 2_000_000;

function folder() {
  return join(process.cwd(), 'public', 'brand');
}

function listed(slot: BrandSlot) {
  const dir = folder();
  if (!existsSync(dir)) return null;
  const name = readdirSync(dir).find((file) => file.startsWith(`${slot}.`) && !file.endsWith('.part'));
  if (!name) return null;
  const path = join(dir, name);
  return { path, name, modified: Math.floor(statSync(path).mtimeMs) };
}

export function brandType(name: string) {
  if (name.endsWith('.png')) return 'image/png';
  if (name.endsWith('.jpg') || name.endsWith('.jpeg')) return 'image/jpeg';
  if (name.endsWith('.webp')) return 'image/webp';
  if (name.endsWith('.gif')) return 'image/gif';
  if (name.endsWith('.ico')) return 'image/x-icon';
  if (name.endsWith('.svg')) return 'image/svg+xml';
  return 'application/octet-stream';
}

export function brandState() {
  const logo = listed('logo');
  const favicon = listed('favicon');
  return {
    logo: logo ? `/brand/logo?v=${logo.modified}` : '',
    favicon: favicon ? `/brand/favicon?v=${favicon.modified}` : '/favicon.svg',
    faviconType: favicon ? brandType(favicon.name) : 'image/svg+xml',
  };
}

export function brandBytes(slot: BrandSlot) {
  const file = listed(slot);
  if (!file) return null;
  return { bytes: readFileSync(file.path), type: brandType(file.name) };
}

function extension(bytes: Buffer, slot: BrandSlot) {
  if (bytes[0] === 0xff && bytes[1] === 0xd8) return '.jpg';
  if (bytes[0] === 0x89 && bytes[1] === 0x50) return '.png';
  if (bytes.subarray(0, 4).toString() === 'RIFF' && bytes.subarray(8, 12).toString() === 'WEBP') return '.webp';
  if (bytes.subarray(0, 6).toString() === 'GIF87a' || bytes.subarray(0, 6).toString() === 'GIF89a') return '.gif';
  if (slot === 'favicon' && bytes[0] === 0 && bytes[1] === 0 && bytes[2] === 1 && bytes[3] === 0) return '.ico';
  const start = bytes.subarray(0, 300).toString('utf8').trimStart().toLowerCase();
  if (start.startsWith('<svg') || start.startsWith('<?xml')) {
    const text = bytes.toString('utf8').toLowerCase();
    if (!text.includes('<svg') || text.includes('<script') || text.includes('javascript:') || / on[a-z]+\s*=/.test(text)) {
      throw new Error('This SVG cannot be used. Remove scripts and event handlers.');
    }
    return '.svg';
  }
  throw new Error(slot === 'favicon' ? 'Use a PNG, JPG, WEBP, GIF, SVG, or ICO file.' : 'Use a PNG, JPG, WEBP, GIF, or SVG file.');
}

export function saveBrand(slot: BrandSlot, bytes: Buffer) {
  if (bytes.length === 0) throw new Error('Choose an image.');
  if (bytes.length > LIMIT) throw new Error('Use an image under 2 MB.');
  const ext = extension(bytes, slot);
  const dir = folder();
  mkdirSync(dir, { recursive: true });
  for (const file of readdirSync(dir)) {
    if (file.startsWith(`${slot}.`)) rmSync(join(dir, file));
  }
  writeFileSync(join(dir, `${slot}${ext}`), bytes);
}

export function removeBrand(slot: BrandSlot) {
  const dir = folder();
  if (!existsSync(dir)) return;
  for (const file of readdirSync(dir)) {
    if (file.startsWith(`${slot}.`)) rmSync(join(dir, file));
  }
}
