# Quick Test Guide - Session Fix Verification

## Services

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3002 |
| Backend | http://localhost:8000 |

## Test User

| Field | Value |
|-------|-------|
| Email | finaltest@gmail.com |
| Password | TestPassword123 |
| Business | Final Test Business |

## Test Flow (5 Minutes)

### 1. Login ✓
- Go to: http://localhost:3002
- Enter credentials above
- Click "Sign In"
- **Expect:** Redirect to dashboard

### 2. Check Dashboard ✓
- **URL:** http://localhost:3002/
- **Look for:**
  - Business name in header
  - Logout button (top-right)
  - No redirect to login

### 3. Navigate Pages ✓
Test each link:
- Products → http://localhost:3002/products
- Recommendations → http://localhost:3002/recommendations
- Settings → http://localhost:3002/settings

**For each page, verify:**
- ✓ Loads without redirect to login
- ✓ Business name still visible
- ✓ No errors in console (F12)

### 4. Test Session Persistence ✓
- Stay on any page
- Press F5 (refresh)
- **Expect:** Still logged in, no redirect

### 5. Test Logout ✓
- Click "Logout" button (top-right header)
- **Expect:** Redirect to http://localhost:3002/auth/login
- Try accessing: http://localhost:3002/products
- **Expect:** Redirect to login (not logged in anymore)

## Success Criteria

- [ ] Login works
- [ ] All pages accessible without redirect
- [ ] Page refresh maintains session
- [ ] Logout button visible and works
- [ ] No `/login` (404) redirects
- [ ] Correct `/auth/login` redirect

## Bug Fixed?

**Before:** Users redirected to `/login` (404) causing loops
**After:** Correct redirect to `/auth/login` - session persists

## Files Changed

- `/backend/frontend/src/lib/api-client.ts` (line 260)
  - Changed: `/login` → `/auth/login`

## Full Details

See: `/Users/speed/straughter/RCTSv1/speckit/E2E_TEST_REPORT.md`
