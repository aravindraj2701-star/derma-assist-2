import { API_BASE } from '../api/api';

/**
 * Resilient image URL / base64 resolver.
 * Handles:
 * - Direct HTTP/HTTPS URLs
 * - Blob / Object URLs
 * - Data URLs (png, jpeg, webp)
 * - Raw base64 strings with magic byte detection (PNG: iVBORw0KGgo, JPEG: /9j/, WebP: UklGR)
 * - Relative paths (e.g., 'dataset/scin/images/...' or 'uploads/...')
 * - Graceful null handling
 *
 * @param {string|null|undefined} src - Raw image string or path
 * @returns {string|null} - Formatted, browser-renderable image source
 */
export function formatImageSrc(src) {
  if (!src || typeof src !== 'string') {
    return null;
  }

  const trimmed = src.trim();
  if (!trimmed) {
    return null;
  }

  // Already a full data URL, object blob URL, or web URL
  if (
    trimmed.startsWith('data:') ||
    trimmed.startsWith('blob:') ||
    trimmed.startsWith('http://') ||
    trimmed.startsWith('https://')
  ) {
    return trimmed;
  }

  // Detect raw base64 by checking known image magic headers
  if (trimmed.startsWith('iVBOR')) {
    // PNG magic bytes
    return `data:image/png;base64,${trimmed}`;
  }

  if (trimmed.startsWith('/9j/')) {
    // JPEG magic bytes
    return `data:image/jpeg;base64,${trimmed}`;
  }

  if (trimmed.startsWith('UklGR')) {
    // WebP magic bytes
    return `data:image/webp;base64,${trimmed}`;
  }

  if (trimmed.startsWith('R0lGOD')) {
    // GIF magic bytes
    return `data:image/gif;base64,${trimmed}`;
  }

  // Relative dataset path (e.g. "dataset/scin/images/-123.png")
  if (trimmed.startsWith('dataset/') || trimmed.startsWith('/dataset/')) {
    const cleanPath = trimmed.replace(/^\/+/, '');
    return `${API_BASE}/dataset/image?path=${encodeURIComponent(cleanPath)}`;
  }

  // Relative uploads path (e.g. "uploads/scan_1.jpg")
  if (trimmed.startsWith('uploads/') || trimmed.startsWith('/uploads/')) {
    const cleanPath = trimmed.replace(/^\/+/, '');
    return `${API_BASE}/${cleanPath}`;
  }

  // If it looks like base64 (> 80 alphanumeric chars), default to JPEG
  if (trimmed.length > 80 && !trimmed.includes('/') && !trimmed.includes('\\') && !trimmed.includes('?')) {
    return `data:image/jpeg;base64,${trimmed}`;
  }

  // Fallback as relative API path
  if (trimmed.includes('/') || trimmed.includes('.')) {
    const cleanPath = trimmed.replace(/^\/+/, '');
    return `${API_BASE}/${cleanPath}`;
  }

  return `data:image/jpeg;base64,${trimmed}`;
}

/**
 * Log image rendering errors for diagnostics.
 * @param {string} label - Context label (e.g. "Patient Lesion" or "Reference Dataset")
 * @param {string} src - The failed source
 * @param {Event} event - Image error event
 */
export function logImageError(label, src, event) {
  const previewSrc = typeof src === 'string'
    ? (src.startsWith('data:') ? `${src.slice(0, 45)}... [len=${src.length}]` : src)
    : String(src);
  console.warn(`[ImageLoadWarning] Failed to render ${label} image:`, {
    previewSrc,
    event,
    timestamp: new Date().toISOString(),
  });
}

/**
 * Resolves the reference image source from reference example object.
 * @param {Object|null|undefined} refExample
 * @returns {string|null}
 */
export function getReferenceImageSrc(refExample) {
  if (!refExample || typeof refExample !== 'object') return null;
  if (refExample.image_base64) {
    return formatImageSrc(refExample.image_base64);
  }
  if (refExample.image_url) {
    return formatImageSrc(refExample.image_url);
  }
  if (refExample.image_path) {
    return formatImageSrc(refExample.image_path);
  }
  return null;
}
