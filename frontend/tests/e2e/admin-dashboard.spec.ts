/**
 * E2E tests for the admin dashboard.
 *
 * Covers sidebar navigation, active link state, user role management via
 * RoleEditModal, post unpublishing, comment deletion, system health display,
 * and non-admin access prevention. All tests run against a real seeded backend
 * (POST /api/test/seed) with real Clerk authentication.
 */
import { clerk } from '@clerk/testing/playwright'
import { expect, test } from '@playwright/test'
import { waitForAuthToLoad } from '../acceptance/fixtures/helpers'
import { seedWithTestUsers } from '../fixtures/seed-helpers'
import { waitForApiCall } from './fixtures/helpers'

test.describe('Admin Dashboard E2E', () => {
  test.beforeEach(async ({ page }) => {
    await seedWithTestUsers(page.request)

    await page.goto('/')
    await clerk.signIn({ page, emailAddress: 'admin@example.com' })
    await waitForAuthToLoad(page)
  })

  test.describe('Test Group 1: Navigation', () => {
    test('1.1: Admin navigates to /admin/users by default', async ({ page }) => {
      await page.goto('/admin')
      await page.waitForURL('/admin/users')
      await expect(page.locator('nav[aria-label="Admin"]')).toBeVisible()
    })

    test('1.2: Admin navigates between all dashboard sections via sidebar', async ({ page }) => {
      await page.goto('/admin')
      await page.waitForURL('/admin/users')

      await page.locator('nav[aria-label="Admin"]').getByText('Content').click()
      await page.waitForURL('/admin/content')
      await expect(page).toHaveURL('/admin/content')

      await page.locator('nav[aria-label="Admin"]').getByText('System').click()
      await page.waitForURL('/admin/system')
      await expect(page).toHaveURL('/admin/system')

      await page.locator('nav[aria-label="Admin"]').getByText('Users').click()
      await page.waitForURL('/admin/users')
      await expect(page).toHaveURL('/admin/users')
    })
  })

  test.describe('Test Group 2: Active Link Highlighting', () => {
    test('2.1: Active sidebar link has aria-current="page"; inactive links do not', async ({
      page,
    }) => {
      await page.goto('/admin/content')
      await waitForAuthToLoad(page)

      const contentLink = page.locator('nav[aria-label="Admin"]').getByText('Content')
      await expect(contentLink).toHaveAttribute('aria-current', 'page')

      const usersLink = page.locator('nav[aria-label="Admin"]').getByText('Users')
      await expect(usersLink).not.toHaveAttribute('aria-current', 'page')
    })
  })

  test.describe('Test Group 3: User Role Management', () => {
    test('3.1: Admin changes a user role via the role edit modal', async ({ page }) => {
      await page.goto('/admin/users')
      await expect(page.getByRole('table')).toBeVisible()

      await page.getByRole('button', { name: 'Edit Role' }).first().click()
      await expect(page.getByRole('dialog')).toBeVisible()

      await page.locator('input[type="radio"][value="admin"]').click()
      await expect(page.getByRole('dialog').getByRole('button', { name: 'Save' })).toBeEnabled()

      const roleUpdatePromise = waitForApiCall(page, '/admin/users', 5000)
      await page.getByRole('dialog').getByRole('button', { name: 'Save' }).click()
      await roleUpdatePromise

      await expect(page.getByRole('dialog')).not.toBeVisible()
      await expect(page.getByRole('table')).toContainText('admin')
    })

    test('3.2: Cancel button dismisses role edit modal without saving', async ({ page }) => {
      await page.goto('/admin/users')
      await expect(page.getByRole('table')).toBeVisible()

      await page.getByRole('button', { name: 'Edit Role' }).first().click()
      await expect(page.getByRole('dialog')).toBeVisible()

      await page.getByRole('dialog').getByRole('button', { name: 'Cancel' }).click()
      await expect(page.getByRole('dialog')).not.toBeVisible()
    })
  })

  test.describe('Test Group 4: Post Moderation', () => {
    test('4.1: Admin unpublishes a post via the confirmation modal', async ({ page }) => {
      await page.goto('/admin/content')
      await expect(page.locator('button[role="tab"]:has-text("Posts")')).toBeVisible()

      await page.locator('button[role="tab"]:has-text("Posts")').click()
      await expect(page.getByRole('table')).toBeVisible()

      await page.getByRole('button', { name: 'Unpublish' }).first().click()
      await expect(page.getByRole('dialog')).toBeVisible()
      await expect(page.getByRole('dialog')).toContainText('Unpublish')

      const unpublishPromise = waitForApiCall(page, '/admin/posts', 5000)
      await page.getByRole('dialog').getByRole('button', { name: 'Unpublish' }).click()
      await unpublishPromise
      await expect(page.getByRole('dialog')).not.toBeVisible()
    })
  })

  test.describe('Test Group 5: Comment Moderation', () => {
    test('5.1: Admin deletes a comment via the confirmation modal', async ({ page }) => {
      await page.goto('/admin/content')
      await expect(page.locator('button[role="tab"]:has-text("Comments")')).toBeVisible()

      await page.locator('button[role="tab"]:has-text("Comments")').click()
      await expect(page.getByRole('table')).toBeVisible()

      await page.getByRole('button', { name: 'Delete' }).first().click()
      await expect(page.getByRole('dialog')).toBeVisible()

      const deletePromise = waitForApiCall(page, '/admin/comments', 5000)
      await page.getByRole('dialog').getByRole('button', { name: 'Delete' }).click()
      await deletePromise
      await expect(page.getByRole('dialog')).not.toBeVisible()
    })
  })

  test.describe('Test Group 6: System Health', () => {
    test('6.1: System health page renders status indicators with colour coding', async ({
      page,
    }) => {
      await page.goto('/admin/system')

      const healthSection = page.locator('section[aria-label="System health"]')
      await expect(healthSection).toBeVisible()

      const statusText = await healthSection.textContent()
      expect(statusText).not.toBeNull()
      expect(statusText).toMatch(/Healthy|Degraded|Unhealthy/)

      const colourDot = healthSection
        .locator('[class*="bg-green-500"], [class*="bg-yellow-500"], [class*="bg-red-500"]')
        .first()
      await expect(colourDot).toBeVisible()
    })
  })
})

test.describe('Non-admin access', () => {
  test.beforeEach(async ({ page }) => {
    await seedWithTestUsers(page.request)

    await page.goto('/')
    await clerk.signIn({ page, emailAddress: 'author@example.com' })
    await waitForAuthToLoad(page)
  })

  test('7.1: Non-admin user is redirected to /forbidden when accessing /admin', async ({
    page,
  }) => {
    await page.goto('/admin')
    await expect(page).toHaveURL('/forbidden')
  })
})
