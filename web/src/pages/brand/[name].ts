import type { APIRoute } from 'astro';
import { brandBytes, type BrandSlot } from '../../lib/brand';

export const prerender = false;

export const GET: APIRoute = ({ params }) => {
  const name = params.name;
  if (name !== 'logo' && name !== 'favicon') return new Response(null, { status: 404 });
  const file = brandBytes(name as BrandSlot);
  if (!file) return new Response(null, { status: 404 });
  return new Response(file.bytes, {
    headers: {
      'content-type': file.type,
      'cache-control': 'public, max-age=3600',
    },
  });
};
