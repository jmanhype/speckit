"""
Response Compression Middleware

Compresses HTTP responses using gzip to reduce bandwidth usage.
Only compresses responses larger than 500 bytes.
"""

from starlette.middleware.gzip import GZipMiddleware as BaseGZipMiddleware


class CompressionMiddleware(BaseGZipMiddleware):
    """
    GZip compression middleware with sensible defaults

    Configuration:
    - Minimum size: 500 bytes (don't compress tiny responses)
    - Compression level: 6 (balance between speed and compression ratio)
    - Compressible types: text/*, application/json, application/javascript

    Usage in main.py:
        app.add_middleware(CompressionMiddleware, minimum_size=500, compresslevel=6)

    Performance impact:
    - Reduces bandwidth by 60-80% for text content
    - Adds ~1-5ms latency for compression
    - Saves significant time on slow networks
    """

    def __init__(self, app, minimum_size: int = 500, compresslevel: int = 6):
        """
        Initialize compression middleware

        Args:
            app: ASGI application
            minimum_size: Minimum response size in bytes to compress (default: 500)
            compresslevel: Gzip compression level 1-9 (default: 6)
                          1 = fastest, least compression
                          9 = slowest, most compression
                          6 = good balance
        """
        super().__init__(app, minimum_size=minimum_size, compresslevel=compresslevel)
