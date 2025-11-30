/**
 * E2E tests for recommendation generation flow
 *
 * Tests the complete user journey from login to recommendation generation.
 *
 * Run with: npx playwright test
 */

import { test, expect } from '@playwright/test';

test.describe('Recommendation Generation Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to app
    await page.goto('http://localhost:3000');
  });

  test('complete recommendation workflow', async ({ page }) => {
    // 1. Login
    await page.click('text=Login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');

    // Wait for dashboard
    await page.waitForSelector('text=Dashboard');
    await expect(page).toHaveURL(/\/dashboard/);

    // 2. Navigate to recommendations
    await page.click('text=Recommendations');
    await expect(page).toHaveURL(/\/recommendations/);

    // 3. Generate new recommendation
    await page.click('text=Generate Recommendation');

    // Select market date
    await page.fill('input[name="marketDate"]', '2025-02-15');

    // Select venue
    await page.click('select[name="venueId"]');
    await page.click('option:has-text("Farmers Market")');

    // Select products
    await page.check('input[type="checkbox"][data-product-id="product-1"]');
    await page.check('input[type="checkbox"][data-product-id="product-2"]');

    // Submit
    await page.click('button:has-text("Generate")');

    // 4. Wait for results
    await page.waitForSelector('.recommendation-result', { timeout: 10000 });

    // Verify recommendation appears
    const recommendation = page.locator('.recommendation-result').first();
    await expect(recommendation).toContainText('Recommended Quantity');
    await expect(recommendation).toContainText('Confidence');

    // 5. Accept recommendation
    await page.click('button:has-text("Accept Recommendation")');

    // Verify success message
    await expect(page.locator('.success-message')).toBeVisible();
  });

  test('submit feedback on recommendation', async ({ page }) => {
    // Assume logged in
    await page.goto('http://localhost:3000/recommendations');

    // Navigate to past recommendation
    await page.click('.recommendation-card:first-child');

    // Click feedback button
    await page.click('button:has-text("Submit Feedback")');

    // Fill feedback form
    await page.fill('input[name="actualQuantitySold"]', '25');
    await page.click('.star-rating .star:nth-child(4)'); // 4 stars

    // Submit
    await page.click('button:has-text("Submit Feedback")');

    // Verify success
    await expect(page.locator('.success-message')).toContainText('Feedback submitted');

    // Verify variance calculation appears
    await expect(page.locator('.variance-indicator')).toBeVisible();
  });

  test('view analytics dashboard', async ({ page }) => {
    await page.goto('http://localhost:3000/analytics');

    // Verify charts load
    await page.waitForSelector('.chart-container');

    // Verify key metrics
    await expect(page.locator('.metric-card')).toHaveCount(4); // 4 key metrics

    // Test date range filter
    await page.click('select[name="dateRange"]');
    await page.click('option:has-text("Last 30 Days")');

    // Verify chart updates
    await page.waitForTimeout(1000); // Wait for chart re-render
    await expect(page.locator('.chart-container')).toBeVisible();
  });

  test('error handling - API failure', async ({ page }) => {
    // Mock API failure
    await page.route('**/api/v1/recommendations/generate', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' }),
      });
    });

    await page.goto('http://localhost:3000/recommendations/new');

    // Fill form
    await page.fill('input[name="marketDate"]', '2025-02-15');

    // Submit
    await page.click('button:has-text("Generate")');

    // Verify error message appears
    await expect(page.locator('.error-message')).toContainText('Failed to generate recommendation');
  });

  test('accessibility - keyboard navigation', async ({ page }) => {
    await page.goto('http://localhost:3000');

    // Tab through navigation
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter'); // Activate link

    // Verify navigation worked
    await expect(page).toHaveURL(/\/(dashboard|recommendations)/);
  });
});

test.describe('Mobile Responsiveness', () => {
  test.use({ viewport: { width: 375, height: 667 } }); // iPhone SE

  test('mobile navigation', async ({ page }) => {
    await page.goto('http://localhost:3000');

    // Verify mobile menu button exists
    await expect(page.locator('.mobile-menu-button')).toBeVisible();

    // Click menu
    await page.click('.mobile-menu-button');

    // Verify menu opens
    await expect(page.locator('.mobile-menu')).toBeVisible();
  });

  test('mobile recommendation form', async ({ page }) => {
    await page.goto('http://localhost:3000/recommendations/new');

    // Verify form is usable on mobile
    await expect(page.locator('input[name="marketDate"]')).toBeVisible();
    await expect(page.locator('select[name="venueId"]')).toBeVisible();

    // Verify submit button is accessible
    const submitButton = page.locator('button:has-text("Generate")');
    await expect(submitButton).toBeVisible();

    // Verify no horizontal scrolling
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const windowWidth = await page.evaluate(() => window.innerWidth);
    expect(bodyWidth).toBeLessThanOrEqual(windowWidth + 1); // +1 for rounding
  });
});
