# Quality Assurance Procedures

This document outlines QA validation procedures for production readiness.

## T176: Full Test Suite & Coverage

**Objective**: Ensure ≥90% test coverage across the codebase

### Backend Test Coverage

```bash
cd backend

# Run full test suite with coverage
pytest --cov=src --cov-report=html --cov-report=term --cov-report=xml

# View coverage report
open htmlcov/index.html

# Check coverage percentage
pytest --cov=src --cov-report=term | grep "TOTAL"
```

**Success Criteria**:
- Overall coverage ≥90%
- Critical paths (auth, payment, prediction) at 100%
- All tests passing

### Frontend Test Coverage

```bash
cd frontend

# Run tests with coverage
npm test -- --coverage --watchAll=false

# View coverage report
open coverage/lcov-report/index.html
```

**Success Criteria**:
- Overall coverage ≥80%
- All component tests passing

## T177: Accessibility Audit (WCAG 2.1 AA)

**Objective**: Ensure WCAG 2.1 Level AA compliance

### Automated Testing

```bash
cd frontend

# Install axe-core
npm install --save-dev @axe-core/cli

# Run accessibility tests
npx axe http://localhost:3000 --tags wcag2a,wcag2aa
```

### Manual Testing Checklist

- [ ] **Keyboard Navigation**
  - All interactive elements accessible via Tab
  - Focus indicators visible
  - Skip links present
  - No keyboard traps

- [ ] **Screen Reader Compatibility**
  - Test with NVDA (Windows) or VoiceOver (Mac)
  - All images have alt text
  - Form labels properly associated
  - ARIA landmarks used correctly

- [ ] **Color Contrast**
  - Text contrast ratio ≥4.5:1 (normal text)
  - Text contrast ratio ≥3:1 (large text)
  - UI controls contrast ≥3:1

- [ ] **Form Accessibility**
  - All inputs have labels
  - Error messages clearly identified
  - Required fields marked
  - Autocomplete attributes present

- [ ] **Touch Targets**
  - Minimum 44x44px touch targets (mobile)
  - Adequate spacing between targets

### Tools

- **Chrome DevTools**: Lighthouse accessibility audit
- **axe DevTools**: Browser extension for automated checks
- **WAVE**: Web accessibility evaluation tool
- **Color Contrast Analyzer**: Check contrast ratios

**Success Criteria**:
- 0 critical accessibility violations
- All WCAG 2.1 AA criteria met
- Manual keyboard navigation smooth

## T178: Lighthouse Performance Audit (Mobile)

**Objective**: Ensure mobile performance meets targets

### Running Lighthouse

```bash
# Install Lighthouse CLI
npm install -g lighthouse

# Run mobile audit
lighthouse https://your-app.com \
  --output html \
  --output-path ./lighthouse-mobile.html \
  --preset perf \
  --emulated-form-factor=mobile \
  --throttling-method=simulate

# View report
open lighthouse-mobile.html
```

### Performance Targets

- **Performance Score**: ≥90/100
- **First Contentful Paint (FCP)**: <1.8s
- **Speed Index**: <3.4s
- **Largest Contentful Paint (LCP)**: <2.5s
- **Time to Interactive (TTI)**: <3.8s
- **Total Blocking Time (TBT)**: <200ms
- **Cumulative Layout Shift (CLS)**: <0.1

### Optimization Checklist

- [ ] Images optimized and properly sized
- [ ] Code splitting implemented
- [ ] Lazy loading for routes
- [ ] Service worker caching enabled
- [ ] CSS minified
- [ ] JavaScript minified
- [ ] Gzip/Brotli compression enabled
- [ ] CDN used for static assets
- [ ] Critical CSS inlined
- [ ] Fonts optimized (preload, swap)

**Success Criteria**:
- Lighthouse Performance score ≥90
- All Core Web Vitals in "Good" range
- Mobile load time <3 seconds on 3G

## T179: Checklist Validation

**Objective**: Validate all items from project checklists

### Security Checklist

From `specs/001-market-inventory-predictor/checklists/security.md`:

- [ ] HTTPS enforced
- [ ] CSRF protection enabled
- [ ] Input sanitization implemented
- [ ] SQL injection prevention verified
- [ ] XSS prevention verified
- [ ] Authentication tokens secure (JWT)
- [ ] Password hashing (bcrypt/argon2)
- [ ] Rate limiting configured
- [ ] Security headers set (CSP, HSTS, X-Frame-Options)
- [ ] Secrets not in code (environment variables)
- [ ] Dependencies scanned for vulnerabilities
- [ ] API endpoints require authentication
- [ ] File upload restrictions

### Performance Checklist

From `specs/001-market-inventory-predictor/checklists/performance.md`:

- [ ] Database queries optimized (indexes)
- [ ] N+1 queries eliminated
- [ ] Redis caching implemented
- [ ] API response compression (gzip)
- [ ] Frontend bundle size <500KB
- [ ] Images optimized (WebP, lazy load)
- [ ] Code splitting enabled
- [ ] Service worker caching
- [ ] CDN configured
- [ ] Database connection pooling
- [ ] Query timeouts set
- [ ] Pagination for large datasets

### Compliance Checklist

From `specs/001-market-inventory-predictor/checklists/gdpr.md`:

- [ ] Data export endpoint (GDPR right to access)
- [ ] Data deletion endpoint (GDPR right to deletion)
- [ ] Consent management
- [ ] Privacy policy accessible
- [ ] Cookie consent banner
- [ ] Data retention policies configured
- [ ] Audit trail for data access
- [ ] Encryption at rest
- [ ] Encryption in transit (TLS)
- [ ] Data minimization principle followed
- [ ] User notification for breaches

### Accessibility Checklist

From `specs/001-market-inventory-predictor/checklists/accessibility.md`:

- [ ] WCAG 2.1 AA compliance
- [ ] Keyboard navigation
- [ ] Screen reader tested
- [ ] Color contrast sufficient
- [ ] Alt text for images
- [ ] Form labels present
- [ ] ARIA attributes used correctly
- [ ] Focus management
- [ ] Skip links present
- [ ] Responsive design (mobile-friendly)

## Success Criteria Summary

**T176**: Test coverage ≥90%, all tests passing
**T177**: WCAG 2.1 AA compliance, 0 critical violations
**T178**: Lighthouse score ≥90, Core Web Vitals "Good"
**T179**: All checklist items verified and passing

## Reporting

Document results in:
- `docs/TEST_COVERAGE_REPORT.md`
- `docs/ACCESSIBILITY_AUDIT_REPORT.md`
- `docs/PERFORMANCE_AUDIT_REPORT.md`
- `docs/COMPLIANCE_CHECKLIST_STATUS.md`

## Continuous Monitoring

Set up automated checks:
- CI/CD integration for test coverage
- Lighthouse CI for performance regression
- axe-core in CI for accessibility
- Dependency scanning (Dependabot, Snyk)
