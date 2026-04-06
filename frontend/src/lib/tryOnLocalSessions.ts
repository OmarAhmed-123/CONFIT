/**
 * Local try-on session history (development / offline-first substitute for Supabase-backed storage).
 * Persists compact thumbnails + metadata in localStorage; no network calls.
 */

const STORAGE_KEY = 'confit_tryon_sessions_v1';
const MAX_ENTRIES = 8;
const THUMB_MAX_W = 140;

export interface TryOnLocalSessionEntry {
  id: string;
  createdAt: string;
  productId: string;
  productName: string;
  thumbDataUrl: string;
}

function loadRaw(): TryOnLocalSessionEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (x): x is TryOnLocalSessionEntry =>
        typeof x === 'object' &&
        x !== null &&
        typeof (x as TryOnLocalSessionEntry).id === 'string' &&
        typeof (x as TryOnLocalSessionEntry).thumbDataUrl === 'string'
    );
  } catch {
    return [];
  }
}

function saveRaw(entries: TryOnLocalSessionEntry[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch {
    // Quota exceeded or private mode — fail silently
  }
}

function makeThumb(dataUrl: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      try {
        const scale = THUMB_MAX_W / img.naturalWidth;
        const w = Math.round(Math.min(THUMB_MAX_W, img.naturalWidth));
        const h = Math.round(img.naturalHeight * Math.min(scale, 1));
        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          resolve('');
          return;
        }
        ctx.drawImage(img, 0, 0, w, h);
        resolve(canvas.toDataURL('image/jpeg', 0.72));
      } catch {
        resolve('');
      }
    };
    img.onerror = () => reject(new Error('thumb load failed'));
    img.src = dataUrl;
  });
}

export function listTryOnSessions(): TryOnLocalSessionEntry[] {
  return loadRaw().sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  );
}

export async function appendTryOnSession(opts: {
  resultImageDataUrl: string;
  productId: string;
  productName: string;
}): Promise<void> {
  let thumb = '';
  try {
    thumb = await makeThumb(opts.resultImageDataUrl);
  } catch {
    thumb = '';
  }

  const entry: TryOnLocalSessionEntry = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    createdAt: new Date().toISOString(),
    productId: opts.productId,
    productName: opts.productName,
    thumbDataUrl: thumb,
  };

  const next = [entry, ...loadRaw()].slice(0, MAX_ENTRIES);
  saveRaw(next);
}

export function clearTryOnSessions() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
