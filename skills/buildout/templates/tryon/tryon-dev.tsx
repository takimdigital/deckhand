'use client';
/**
 * TryOnDev — mounted once by tryon_install into app/layout.tsx (dev-only, reversible).
 * Gate: NODE_ENV === "development" (verified: `next build` output contains no trace of this).
 * The overlay itself is served by the local helper (tryon_server.py) — nothing is bundled.
 */
import { useEffect } from 'react';

const PORT = Number('__TRYON_PORT__');
const TOKEN = '__TRYON_TOKEN__';

export default function TryOnDev() {
  useEffect(() => {
    if (process.env.NODE_ENV !== 'development') return;
    if (document.querySelector('script[data-tryon]')) return;
    const s = document.createElement('script');
    s.src = `http://127.0.0.1:${PORT}/overlay.js?token=${TOKEN}`;
    s.async = true;
    s.dataset.tryon = '1';
    document.body.appendChild(s);
    return () => {
      s.remove();
    };
  }, []);
  return null;
}
