/**
 * End-to-end tests for Heaven GUI
 * Using Playwright
 */

import { test, expect } from '@playwright/test';

test.describe('Heaven GUI', () => {
  test.beforeEach(async ({ page }) => {
    // The Playwright test runner should launch the Tauri app and provide the window context.
    // No need to navigate to a URL; Playwright is already connected to the app window.
    // (Removed invalid page.goto('tauri://localhost'))
  });

  test('should load main interface', async ({ page }) => {
    // Check that the main interface loads
    await expect(page.locator('h1')).toContainText('Heaven');
    
    // Check for main sections
    await expect(page.locator('[data-testid="file-browser"]')).toBeVisible();
    await expect(page.locator('[data-testid="code-editor"]')).toBeVisible();
    await expect(page.locator('[data-testid="commit-graph"]')).toBeVisible();
  });

  test('should open command palette with Cmd+K', async ({ page }) => {
    // Press Cmd+K (or Ctrl+K on Windows/Linux)
    await page.keyboard.press('Meta+K');
    
    // Command palette should be visible
    await expect(page.locator('.command-palette')).toBeVisible();
    
    // Should have search input
    await expect(page.locator('.command-palette input[type="text"]')).toBeFocused();
  });

  test('should create workpad', async ({ page }) => {
    // Open command palette
    await page.keyboard.press('Meta+K');
    
    // Type command to create workpad
    await page.fill('.command-palette input', 'create workpad');
    await page.keyboard.press('Enter');
    
    // Fill workpad creation form
    await page.fill('[placeholder="New workpad title..."]', 'test-feature');
    await page.click('button:has-text("Create Workpad")');
    
    // Check success notification
    await expect(page.locator('.toast')).toContainText('created successfully');
    
    // Check workpad appears in list
    await expect(page.locator('[data-testid="workpad-list"]')).toContainText('test-feature');
  });

  test('should render commit graph', async ({ page }) => {
    // Navigate to commit graph tab
    await page.click('[data-testid="commit-graph-tab"]');
    
    // Check that D3 SVG graph is rendered
    await expect(page.locator('svg.commit-graph')).toBeVisible();
    
    // Check for commit nodes
    const nodes = page.locator('.commit-node');
    await expect(nodes.first()).toBeVisible();
  });

  test('should display test results', async ({ page }) => {
    // Navigate to tests tab
    await page.click('[data-testid="tests-tab"]');
    
    // Check test results are visible
    await expect(page.locator('.test-result')).toBeVisible();
    
    // Should show test status
    await expect(page.locator('.test-status')).toHaveText(/passed|failed|running/i);
  });

  test('should switch between light and dark theme', async ({ page }) => {
    // Open settings
    await page.click('[data-testid="settings-button"]');
    
    // Toggle theme
    await page.click('[data-testid="theme-toggle"]');
    
    // Check theme changed
    const html = page.locator('html');
    await expect(html).toHaveAttribute('data-theme', /light|dark/);
  });

  test('should search files', async ({ page }) => {
    // Open file search (Cmd+P)
    await page.keyboard.press('Meta+P');
    
    // Type search query
    await page.fill('.file-search input', 'test.py');
    
    // Should show matching files
    await expect(page.locator('.search-result')).toContainText('test.py');
    
    // Click on result to open file
    await page.click('.search-result:first-child');
    
    // File should open in editor
    await expect(page.locator('.monaco-editor')).toBeVisible();
  });

  test('should handle keyboard shortcuts', async ({ page }) => {
    // Test various keyboard shortcuts
    const shortcuts = [
      { key: 'Meta+S', action: 'save' },
      { key: 'Meta+K', action: 'command-palette' },
      { key: 'Meta+P', action: 'file-search' },
      { key: 'Meta+/', action: 'toggle-comment' },
    ];
    
    for (const { key, action } of shortcuts) {
      await page.keyboard.press(key);
      // Check that appropriate UI element appears
      await expect(page.locator(`[data-action="${action}"]`)).toBeVisible();
      
      // Close it (press Escape)
      await page.keyboard.press('Escape');
    }
  });

  test('should run tests from GUI', async ({ page }) => {
    // Select a workpad
    await page.click('[data-testid="workpad-list"] .workpad-item:first-child');
    
    // Click run tests button
    await page.click('button:has-text("Run Tests")');
    
    // Should show loading indicator
    await expect(page.locator('.test-runner-loading')).toBeVisible();
    
    // Wait for tests to complete
    await page.waitForSelector('.test-results', { timeout: 30000 });
    
    // Should show test results
    await expect(page.locator('.test-results')).toBeVisible();
  });

  test('should promote workpad', async ({ page }) => {
    // Select a workpad
    await page.click('[data-testid="workpad-list"] .workpad-item:first-child');
    
    // Click promote button
    await page.click('button:has-text("Promote")');
    
    // Confirm promotion
    await page.click('button:has-text("Confirm")');
    
    // Should show success message
    await expect(page.locator('.toast')).toContainText('promoted successfully');
  });

  test('should display AI assistant panel', async ({ page }) => {
    // Check AI panel is visible
    await expect(page.locator('[data-testid="ai-panel"]')).toBeVisible();
    
    // Type a query
    await page.fill('[data-testid="ai-input"]', 'Generate unit tests for this file');
    await page.keyboard.press('Enter');
    
    // Should show loading state
    await expect(page.locator('[data-testid="ai-loading"]')).toBeVisible();
    
    // Wait for response
    await page.waitForSelector('[data-testid="ai-response"]', { timeout: 10000 });
    
    // Should display AI response
    await expect(page.locator('[data-testid="ai-response"]')).toBeVisible();
  });
});

test.describe('Heaven GUI Performance', () => {
  test('should render quickly on startup', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('tauri://localhost');
    
    // Wait for main UI to be interactive
    await page.waitForSelector('[data-testid="code-editor"]');
    
    const loadTime = Date.now() - startTime;
    
    // Should load in less than 3 seconds
    expect(loadTime).toBeLessThan(3000);
  });

  test('should handle large files efficiently', async ({ page }) => {
    // Open a large file
    await page.click('[data-testid="file-browser"] >> text=large-file.py');
    
    const startTime = Date.now();
    await page.waitForSelector('.monaco-editor');
    
    const renderTime = Date.now() - startTime;
    
    // Should render in less than 500ms
    expect(renderTime).toBeLessThan(500);
  });

  test('should scroll smoothly', async ({ page }) => {
    // Open file with many lines
    await page.click('[data-testid="file-browser"] >> text=long-file.py');
    
    // Measure scroll performance
    const scrollStart = Date.now();
    for (let i = 0; i < 10; i++) {
      await page.mouse.wheel(0, 100);
      await page.waitForTimeout(50);
    }
    const scrollTime = Date.now() - scrollStart;
    
    // Should scroll smoothly (less than 1 second for 10 scrolls)
    expect(scrollTime).toBeLessThan(1000);
  });
});

test.describe('Heaven GUI Accessibility', () => {
  test('should be keyboard navigable', async ({ page }) => {
    await page.goto('tauri://localhost');
    
    // Tab through focusable elements
    for (let i = 0; i < 5; i++) {
      await page.keyboard.press('Tab');
      const focused = await page.evaluate(() => document.activeElement?.tagName);
      expect(focused).toBeTruthy();
    }
  });

  test('should have proper ARIA labels', async ({ page }) => {
    await page.goto('tauri://localhost');
    
    // Check main sections have ARIA labels
    const sections = [
      '[data-testid="file-browser"]',
      '[data-testid="code-editor"]',
      '[data-testid="commit-graph"]',
    ];
    
    for (const selector of sections) {
      const ariaLabel = await page.locator(selector).getAttribute('aria-label');
      expect(ariaLabel).toBeTruthy();
    }
  });

  test('should support screen reader navigation', async ({ page }) => {
    await page.goto('tauri://localhost');
    
    // Check for landmark roles
    await expect(page.locator('[role="main"]')).toBeVisible();
    await expect(page.locator('[role="navigation"]')).toBeVisible();
    await expect(page.locator('[role="complementary"]')).toBeVisible();
  });
});
