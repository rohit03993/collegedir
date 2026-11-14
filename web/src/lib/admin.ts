import { ApiError } from './api';

export const fieldClass = 'h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none focus:border-orange-400';
export const areaClass = 'w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm leading-6 text-slate-900 outline-none focus:border-orange-400';

function apiBase() {
  const configured = import.meta.env.API_URL;
  return configured || 'http://127.0.0.1:8000';
}

export async function adminFetch<T>(token: string | undefined, path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (init.body && !headers.has('content-type')) headers.set('content-type', 'application/json');
  let response: Response;
  try {
    response = await fetch(`${apiBase()}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(503, 'Start the catalogue API at http://127.0.0.1:8000.');
  }
  if (!response.ok) {
    let detail = '';
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') detail = body.detail;
    } catch {
      detail = '';
    }
    if (response.status === 404) detail = 'Restart the catalogue API so the admin routes load.';
    throw new ApiError(response.status, detail || 'The admin request failed.');
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export function tokenFrom(cookies: { get(name: string): { value: string } | undefined }) {
  return cookies.get('setu_staff')?.value || '';
}

export function saveSession(cookies: { set(name: string, value: string, options: Record<string, unknown>): void }, token: string) {
  cookies.set('setu_staff', token, {
    httpOnly: true,
    path: '/',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 14,
  });
}

export function clearSession(cookies: { delete(name: string, options: { path: string }): void }) {
  cookies.delete('setu_staff', { path: '/' });
}
