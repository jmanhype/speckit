# Security Guide

## Overview

MarketPrep implements multiple layers of security to protect vendor data and prevent common web application vulnerabilities.

## Security Layers

### 1. Transport Security (HTTPS)

**Production Requirements:**
- All traffic MUST use HTTPS (enforced via HSTS headers)
- TLS 1.2 or higher required
- Valid SSL certificate from trusted CA

**Headers:**
```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

### 2. Security Headers

Implemented via `SecurityHeadersMiddleware`:

| Header | Value | Purpose |
|--------|-------|---------|
| X-Frame-Options | DENY | Prevent clickjacking attacks |
| X-Content-Type-Options | nosniff | Prevent MIME sniffing |
| X-XSS-Protection | 1; mode=block | Enable browser XSS filter |
| Strict-Transport-Security | max-age=31536000 | Enforce HTTPS |
| Content-Security-Policy | default-src 'self' | Control resource loading |
| Referrer-Policy | strict-origin-when-cross-origin | Control referrer info |
| Permissions-Policy | geolocation=(), microphone=() | Disable dangerous features |

### 3. Authentication & Authorization

**JWT-based Authentication:**
- Access tokens expire in 15 minutes (configurable)
- Refresh tokens expire in 7 days
- HS256 algorithm (symmetric signing)
- Tokens include vendor_id for multi-tenancy

**Password Security:**
- Bcrypt hashing with automatic salt
- Minimum password requirements enforced
- No password hints or recovery via email

**API Keys:**
- SHA256 hashed before storage
- 90-day rotation recommended
- Format: `mp_<64_hex_chars>`

### 4. Input Validation & Sanitization

**All user input is validated:**

```python
from src.security import InputValidator, sanitize_html

# HTML sanitization
safe_text = sanitize_html(user_input, max_length=1000)

# Email validation
if InputValidator.validate_email(email):
    # Process email

# Filename sanitization
safe_filename = InputValidator.sanitize_filename(uploaded_filename)

# Path traversal prevention
if not InputValidator.validate_no_path_traversal(file_path):
    raise HTTPException(400, "Invalid path")
```

**Automatic checks for:**
- SQL injection patterns
- XSS attempts
- Path traversal
- Command injection
- HTML injection

### 5. SQL Injection Prevention

**Multiple layers of defense:**

1. **SQLAlchemy ORM** (primary defense)
   - All queries use parameterized statements
   - Never use raw SQL with user input

2. **Input validation** (defense-in-depth)
   - Detects suspicious SQL patterns
   - Logs potential injection attempts

**Best Practices:**
```python
# ✅ GOOD - Parameterized query
products = db.query(Product).filter(Product.name == user_input).all()

# ❌ BAD - String concatenation
db.execute(f"SELECT * FROM products WHERE name = '{user_input}'")

# ✅ GOOD - Use text() with parameters
from sqlalchemy import text
db.execute(text("SELECT * FROM products WHERE name = :name"), {"name": user_input})
```

### 6. Cross-Site Scripting (XSS) Prevention

**Server-side:**
- All output is HTML-escaped by default
- Use `sanitize_html()` for user-generated content
- Content-Security-Policy headers restrict inline scripts

**Client-side (React):**
- React escapes content by default
- Never use `dangerouslySetInnerHTML` with user input
- Sanitize data before rendering

### 7. Cross-Site Request Forgery (CSRF)

**Protection:**
- SameSite cookies (when applicable)
- CORS policy restricts origins
- JWT tokens in Authorization header (not cookies)
- State parameter in OAuth flows

### 8. Rate Limiting

**Per-IP limits:**
- Anonymous: 100 requests/minute
- Authenticated: 1000 requests/minute

**Custom endpoint limits:**
```python
from src.middleware.rate_limit import rate_limit

@router.post("/bulk-import", dependencies=[Depends(rate_limit(5, 3600))])
async def bulk_import():
    # Limited to 5 requests per hour
    pass
```

**Graceful degradation:**
- Falls back to no rate limiting if Redis unavailable
- Logs warning when running without rate limits

### 9. Secrets Management

**Encryption:**
```python
from src.security import encrypt_string, decrypt_string

# Encrypt OAuth tokens before storage
encrypted_token = encrypt_string(oauth_token)

# Decrypt when needed
token = decrypt_string(encrypted_token)
```

**API Key Generation:**
```python
from src.security import generate_api_key, hash_api_key

# Generate new key
api_key = generate_api_key(prefix="mp", length=32)
# Returns: "mp_a1b2c3d4..."

# Hash before storing
api_key_hash = hash_api_key(api_key)
```

**Key Rotation:**
```python
from src.security import APIKeyRotation

# Check if key should be rotated (90 days)
if APIKeyRotation.should_rotate_key(created_at):
    # Generate new key
    new_key, key_hash, created = APIKeyRotation.generate_key_pair()
```

### 10. Row-Level Security (RLS)

**Database-level multi-tenancy:**
- All tables include `vendor_id`
- PostgreSQL RLS policies enforce isolation
- Each request sets `app.current_vendor_id`

**Example policy:**
```sql
CREATE POLICY products_isolation ON products
USING (vendor_id = current_setting('app.current_vendor_id')::uuid)
```

### 11. Error Handling

**Information Disclosure Prevention:**
- Production mode hides stack traces
- Generic error messages to clients
- Detailed logs only on server
- Correlation IDs for debugging

**Example:**
```json
// Production error response
{
  "error": true,
  "correlation_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "message": "Internal server error",
  "type": "server_error"
}
```

### 12. Dependency Security

**Regular updates:**
```bash
# Check for vulnerabilities
pip-audit

# Update dependencies
pip install -U -r requirements.txt
```

**Trusted sources only:**
- PyPI packages verified
- Dependency pinning in requirements.txt
- Regular security audits

## Security Checklist

### Development

- [ ] Never commit secrets to git
- [ ] Use `.env` files (gitignored)
- [ ] Validate all user input
- [ ] Use parameterized queries
- [ ] Escape HTML output
- [ ] Enable security headers
- [ ] Test with security scanners

### Deployment

- [ ] Use HTTPS/TLS
- [ ] Set `environment=production`
- [ ] Rotate encryption keys
- [ ] Enable rate limiting
- [ ] Configure log aggregation
- [ ] Set up monitoring/alerting
- [ ] Run security audit
- [ ] Test backup/restore procedures

### Ongoing

- [ ] Rotate API keys every 90 days
- [ ] Review access logs
- [ ] Monitor error rates
- [ ] Update dependencies monthly
- [ ] Security audit quarterly
- [ ] Incident response drills

## Vulnerability Reporting

If you discover a security vulnerability:

1. **DO NOT** open a public GitHub issue
2. Email security@marketprep.example.com
3. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours.

## Security Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Security](https://owasp.org/www-project-api-security/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [SQLAlchemy Security](https://docs.sqlalchemy.org/en/14/faq/security.html)

## Compliance

### GDPR (if applicable)

- User data encryption at rest
- Right to deletion implemented
- Data export capabilities
- Audit logging
- Privacy policy required

### PCI DSS (if handling payments)

- No credit card storage (use Stripe)
- TLS for all transactions
- Access logging
- Regular security audits

## Contact

For security questions: security@marketprep.example.com
