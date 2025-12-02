/**
 * Performance monitoring utilities.
 * Provides Web Vitals tracking and performance metrics.
 */

/**
 * Log performance metrics to console (development only).
 */
export function logPerformanceMetrics(): void {
  if (import.meta.env.DEV) {
    // Log Web Vitals when available
    if ('web-vital' in window) {
      console.log('Web Vitals:', (window as any)['web-vital']);
    }

    // Log Performance API metrics
    const perfData = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    if (perfData) {
      console.log('Performance Metrics:', {
        'DNS Lookup': `${(perfData.domainLookupEnd - perfData.domainLookupStart).toFixed(2)}ms`,
        'TCP Connection': `${(perfData.connectEnd - perfData.connectStart).toFixed(2)}ms`,
        'Request Time': `${(perfData.responseStart - perfData.requestStart).toFixed(2)}ms`,
        'Response Time': `${(perfData.responseEnd - perfData.responseStart).toFixed(2)}ms`,
        'DOM Processing': `${(perfData.domComplete - perfData.domLoading).toFixed(2)}ms`,
        'Total Load Time': `${perfData.loadEventEnd.toFixed(2)}ms`,
      });
    }
  }
}

/**
 * Measure and log the execution time of a function.
 */
export function measurePerformance<T>(
  label: string,
  fn: () => T
): T {
  const start = performance.now();
  const result = fn();
  const end = performance.now();

  if (import.meta.env.DEV) {
    console.log(`[Performance] ${label}: ${(end - start).toFixed(2)}ms`);
  }

  return result;
}

/**
 * Measure and log the execution time of an async function.
 */
export async function measurePerformanceAsync<T>(
  label: string,
  fn: () => Promise<T>
): Promise<T> {
  const start = performance.now();
  const result = await fn();
  const end = performance.now();

  if (import.meta.env.DEV) {
    console.log(`[Performance] ${label}: ${(end - start).toFixed(2)}ms`);
  }

  return result;
}

/**
 * Create a performance mark.
 */
export function mark(name: string): void {
  if ('performance' in window && 'mark' in performance) {
    performance.mark(name);
  }
}

/**
 * Measure the time between two performance marks.
 */
export function measure(name: string, startMark: string, endMark?: string): void {
  if ('performance' in window && 'measure' in performance) {
    try {
      if (endMark) {
        performance.measure(name, startMark, endMark);
      } else {
        performance.measure(name, startMark);
      }

      if (import.meta.env.DEV) {
        const measure = performance.getEntriesByName(name)[0];
        if (measure) {
          console.log(`[Performance] ${name}: ${measure.duration.toFixed(2)}ms`);
        }
      }
    } catch (error) {
      console.error('Performance measure error:', error);
    }
  }
}

/**
 * Get the current memory usage (Chrome only).
 */
export function getMemoryUsage(): { used: number; limit: number } | null {
  if ('memory' in performance) {
    const memory = (performance as any).memory;
    return {
      used: Math.round(memory.usedJSHeapSize / 1048576), // MB
      limit: Math.round(memory.jsHeapSizeLimit / 1048576), // MB
    };
  }
  return null;
}

/**
 * Log bundle sizes and chunk loading times.
 */
export function logBundleInfo(): void {
  if (import.meta.env.DEV) {
    const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
    const scripts = resources.filter((r) => r.name.endsWith('.js'));
    const styles = resources.filter((r) => r.name.endsWith('.css'));

    console.log('Bundle Info:', {
      'Script Count': scripts.length,
      'Style Count': styles.length,
      'Largest Script': scripts.reduce((max, r) =>
        r.transferSize > (max?.transferSize || 0) ? r : max, scripts[0]
      )?.name.split('/').pop(),
      'Total Transfer Size': `${(
        resources.reduce((sum, r) => sum + r.transferSize, 0) / 1024
      ).toFixed(2)} KB`,
    });
  }
}

/**
 * Setup performance monitoring on app load.
 */
export function setupPerformanceMonitoring(): void {
  if (import.meta.env.DEV) {
    // Log metrics when page is fully loaded
    window.addEventListener('load', () => {
      setTimeout(() => {
        logPerformanceMetrics();
        logBundleInfo();

        const memory = getMemoryUsage();
        if (memory) {
          console.log(`Memory Usage: ${memory.used}MB / ${memory.limit}MB`);
        }
      }, 0);
    });
  }
}
