import type { APIRoute } from 'astro';

export const prerender = false;

export const GET: APIRoute = async ({ params }) => {
  const raw = params.path;
  const path = Array.isArray(raw) ? raw.join('/') : raw;
  if (!path) return new Response(null, { status: 404 });
  const base = import.meta.env.API_URL || 'http://127.0.0.1:8000';
  const upstream = await fetch(`${base}/media/${path}`);
  if (!upstream.ok || !upstream.body) return new Response(null, { status: upstream.status });
  return new Response(upstream.body, {
    status: 200,
    headers: {
      'content-type': upstream.headers.get('content-type') || 'image/jpeg',
      'cache-control': 'public, max-age=86400',
    },
  });
};
