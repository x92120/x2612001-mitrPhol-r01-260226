/**
 * Screenshot Capture Script for xMixing Frontend
 * ================================================
 * Captures screenshots of all pages in the application.
 * 
 * Usage:
 *   npx playwright test screenshot-capture.spec.ts
 * 
 * Screenshots saved to: ./screenshots/
 */

import { test } from '@playwright/test';
import * as fs from 'fs';

// Nuxt dev server started on port 3001 when 3000 was already in use.
const BASE_URL = 'http://localhost:3000';
const SCREENSHOT_DIR = './screenshots';

// Test credentials
const TEST_USER = {
    email: 'antigravity',
    password: 'password123'
};

// All pages to capture
const PUBLIC_PAGES = [
    { name: '01-login', path: '/x80-UserLogin' },
    { name: '02-register', path: '/x81-UserRegister' },
];

const AUTH_PAGES = [
    { name: '03-dashboard', path: '/' },
    { name: '04-ingredient-intake', path: '/x10-IngredientIntake' },
    { name: '07-sku-management', path: '/x20-Sku' },
    { name: '08-production-plan', path: '/x30-ProductionPlan' },
    { name: '10-pre-batch', path: '/x40-PreBatch' },
    { name: '10-packing-list', path: '/x50-PackingList' },
    { name: '11-batch-recheck', path: '/x60-BatchRecheck' },
    { name: '12-user-config', path: '/x89-UserConfig' },
    { name: '13-server-status', path: '/x90-adminDashboard' },
    { name: '14-about', path: '/x99-About' },
];

test.describe('Screenshot Capture', () => {
    test.setTimeout(300000); // 5 minutes

    test.beforeAll(async () => {
        if (!fs.existsSync(SCREENSHOT_DIR)) {
            fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
        }
    });

    // Capture public pages
    for (const pageInfo of PUBLIC_PAGES) {
        test(`Capture ${pageInfo.name}`, async ({ page }) => {
            await page.goto(`${BASE_URL}${pageInfo.path}`);
            await page.waitForLoadState('networkidle');
            await page.waitForTimeout(1000);

            await page.screenshot({
                path: `${SCREENSHOT_DIR}/${pageInfo.name}.png`,
                fullPage: true
            });

            console.log(`✅ Captured: ${pageInfo.name}`);
        });
    }

    // Capture authenticated pages
    test('Capture authenticated pages', async ({ page }) => {
        // Go to login page
        await page.goto(`${BASE_URL}/x80-UserLogin`);
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(500);

        // Fill login form using Quasar q-input (nested input inside q-input)
        // Find first input in the form for email
        const emailInput = page.locator('.q-input input').first();
        await emailInput.fill(TEST_USER.email);

        // Find password input
        const passwordInput = page.locator('.q-input input[type="password"]');
        await passwordInput.fill(TEST_USER.password);

        // Click login button - using a more specific selector to avoid strict mode violation with header link
        await page.locator('button.q-btn').filter({ hasText: /^login$/i }).click();

        // Wait for navigation and auth processing
        await page.waitForTimeout(5000);

        // Check if we're logged in by looking at URL or content
        console.log('Current URL:', page.url());

        // Capture each authenticated page
        for (const pageInfo of AUTH_PAGES) {
            try {
                console.log(`📸 Processing: ${pageInfo.name}`);
                await page.goto(`${BASE_URL}${pageInfo.path}`);
                await page.waitForLoadState('networkidle');
                await page.waitForTimeout(2000); // Wait for data loading

                // Main view
                await page.screenshot({
                    path: `${SCREENSHOT_DIR}/${pageInfo.name}.png`,
                    fullPage: true
                });

                // --- DEPTH CAPTURE ---

                // 1. Try to open "New" or "Add" Dialog
                const newBtn = page.locator('button.q-btn').filter({ hasText: /^(Add|New|Create)/i }).first();
                if (await newBtn.isVisible()) {
                    console.log(`   └─ Clicking 'New' button`);
                    await newBtn.click({ force: true });
                    await page.waitForTimeout(2000); // Wait for animation
                    await page.screenshot({ path: `${SCREENSHOT_DIR}/${pageInfo.name}-depth-new.png` });
                    // Close dialog with Escape
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(1000);
                }

                // 2. Try to click first "Edit" or "Action" icon in table
                const actionBtn = page.locator('.q-table tr button.q-btn').first();
                if (await actionBtn.isVisible()) {
                    console.log(`   └─ Clicking first table action`);
                    await actionBtn.click({ force: true });
                    await page.waitForTimeout(2000);
                    await page.screenshot({ path: `${SCREENSHOT_DIR}/${pageInfo.name}-depth-action.png` });
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(1000);
                }

                // 3. Try to open Filters if they exist
                const filterBtn = page.locator('button.q-btn').filter({ hasText: /Filter/i }).first();
                if (await filterBtn.isVisible()) {
                    console.log(`   └─ Clicking 'Filter' button`);
                    await filterBtn.click({ force: true });
                    await page.waitForTimeout(2000);
                    await page.screenshot({ path: `${SCREENSHOT_DIR}/${pageInfo.name}-depth-filter.png` });
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(1000);
                }

                console.log(`✅ Finished: ${pageInfo.name}`);
            } catch (error) {
                console.log(`❌ Failed: ${pageInfo.name} - ${error}`);
            }
        }
    });
});
