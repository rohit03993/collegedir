export const PAGE_SIZE = 20;

export function requestedPage(value: string | null) {
  const requested = Number(value || '1');
  if (!Number.isFinite(requested)) return 1;
  return Math.min(2000, Math.max(1, Math.floor(requested)));
}

export function withPage(path: string, source: URLSearchParams, page: number) {
  const next = new URLSearchParams();
  for (const [key, value] of source.entries()) {
    if (key === 'page' || key === 'per_page') continue;
    next.append(key, value);
  }
  if (page > 1) next.set('page', String(page));
  const text = next.toString();
  return text ? `${path}?${text}` : path;
}

export function pageCount(total: number, pageSize = PAGE_SIZE) {
  return Math.max(1, Math.ceil(total / pageSize));
}
