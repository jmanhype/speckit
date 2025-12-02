/**
 * Image optimization utilities.
 * Provides lazy loading and responsive image helpers.
 */

/**
 * Generate srcset for responsive images.
 */
export function generateSrcSet(
  baseUrl: string,
  widths: number[] = [320, 640, 960, 1280]
): string {
  return widths.map((width) => `${baseUrl}?w=${width} ${width}w`).join(', ');
}

/**
 * Generate sizes attribute for responsive images.
 */
export function generateSizes(breakpoints: { [key: string]: string }): string {
  return Object.entries(breakpoints)
    .map(([media, size]) => `${media} ${size}`)
    .join(', ');
}

/**
 * Lazy load an image with IntersectionObserver.
 */
export function lazyLoadImage(
  img: HTMLImageElement,
  options: IntersectionObserverInit = {}
): () => void {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const target = entry.target as HTMLImageElement;
        const src = target.dataset.src;
        const srcset = target.dataset.srcset;

        if (src) {
          target.src = src;
        }
        if (srcset) {
          target.srcset = srcset;
        }

        target.classList.remove('lazy');
        observer.unobserve(target);
      }
    });
  }, options);

  observer.observe(img);

  // Return cleanup function
  return () => observer.disconnect();
}

/**
 * Preload critical images.
 */
export function preloadImage(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve();
    img.onerror = reject;
    img.src = src;
  });
}

/**
 * Get optimal image format based on browser support.
 */
export function getOptimalImageFormat(): 'webp' | 'avif' | 'jpeg' {
  // Check for AVIF support
  const avifSupport = document
    .createElement('canvas')
    .toDataURL('image/avif')
    .startsWith('data:image/avif');

  if (avifSupport) return 'avif';

  // Check for WebP support
  const webpSupport = document
    .createElement('canvas')
    .toDataURL('image/webp')
    .startsWith('data:image/webp');

  if (webpSupport) return 'webp';

  return 'jpeg';
}
