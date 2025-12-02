# End-to-End Test Plan - Session Persistence Fix

## Test Environment
- Frontend: http://localhost:3002
- Backend: http://localhost:8000
- Fix Applied: Changed `/login` to `/auth/login` in API client's `onAuthError` callback

## Test Steps

### 1. User Registration and Auto-Login
**URL**: http://localhost:3002/register

**Steps**:
1. Navigate to http://localhost:3002/register
2. Fill in registration form:
   - Email: `finaltest@gmail.com`
   - Password: `Test123!`
   - Business Name: `Final Test Business`
3. Click "Register" button
4. **Expected**: Automatic redirect to dashboard at http://localhost:3002/dashboard
5. **Expected**: User should be logged in (check for auth token in localStorage)

**Success Criteria**:
- ✅ Registration succeeds without errors
- ✅ Auto-login occurs (no manual login needed)
- ✅ Redirect to dashboard happens automatically
- ✅ No redirect back to /login page

### 2. Dashboard Navigation Test
**URL**: http://localhost:3002/dashboard

**Steps**:
1. Verify you're on the dashboard page
2. Check page loads completely
3. Look for business name in header/navigation
4. Check for any error messages or console errors

**Success Criteria**:
- ✅ Dashboard loads without redirect to login
- ✅ Business name visible in UI
- ✅ No authentication errors
- ✅ Session persists (no token refresh loops)

### 3. Products Page Navigation
**URL**: http://localhost:3002/products

**Steps**:
1. Click on "Products" link in navigation menu
2. Verify page loads completely
3. Check for logout button visibility

**Success Criteria**:
- ✅ Products page loads without redirect to login
- ✅ Page content displays correctly
- ✅ Logout button should be visible in header/nav

### 4. Recommendations Page Navigation
**URL**: http://localhost:3002/recommendations

**Steps**:
1. Click on "Recommendations" link in navigation menu
2. Verify page loads completely
3. No redirect to login page

**Success Criteria**:
- ✅ Recommendations page loads without redirect
- ✅ Session remains active
- ✅ No authentication errors

### 5. Settings Page Navigation
**URL**: http://localhost:3002/settings

**Steps**:
1. Click on "Settings" link in navigation menu
2. Verify page loads completely
3. No redirect to login page

**Success Criteria**:
- ✅ Settings page loads without redirect
- ✅ User settings display correctly
- ✅ Session remains active

### 6. Logout Functionality Test
**Location**: Header/Navigation area (near business name)

**Steps**:
1. Locate the LOGOUT button in the header/navigation
2. Click the logout button
3. Verify redirect to login page
4. Try accessing http://localhost:3002/dashboard directly
5. **Expected**: Should redirect to login since logged out

**Success Criteria**:
- ✅ Logout button is visible and clearly labeled
- ✅ Clicking logout clears session
- ✅ Redirect to /login page occurs
- ✅ Cannot access protected routes after logout
- ✅ Auth token removed from localStorage

## Critical Bug Being Tested

**Previous Issue**: Session persistence bug where API client's `onAuthError` callback redirected to `/login` instead of `/auth/login`, causing authentication loops and navigation failures.

**Fix Applied**: Updated redirect path from `/login` to `/auth/login`

**Expected Outcome**: All protected routes should load without triggering authentication errors or redirects to login page.

## Test Results

### Registration & Auto-Login
- [ ] Registration successful
- [ ] Auto-login worked
- [ ] Redirected to dashboard
- [ ] No login redirect issues

### Navigation Tests
- [ ] Dashboard loads without redirect
- [ ] Products page loads without redirect
- [ ] Recommendations page loads without redirect
- [ ] Settings page loads without redirect

### Logout Test
- [ ] Logout button visible
- [ ] Logout button functional
- [ ] Redirects to login after logout
- [ ] Cannot access protected routes after logout

### Overall Assessment
- [ ] Session bug FIXED
- [ ] Logout button VISIBLE and WORKING
- [ ] Complete user flow WORKS end-to-end
- [ ] NO remaining critical issues

## Notes
_Add any observations, errors, or issues encountered during testing_

---

**Test Date**: 2025-12-01
**Tester**: _Your Name_
**Build**: Latest with session persistence fix
