import { test, expect } from '@playwright/test';

test.describe('Upkie 课程网站 E2E', () => {
  test('主页加载并显示课程标题', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await expect(page.getByText('Upkie').first()).toBeVisible({ timeout: 15000 });
  });

  test('主页显示阶段列表', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(5000);
    await expect(page.getByText('数学与工具').first()).toBeVisible({ timeout: 10000 });
  });

  test('导航到章节页面并显示标题', async ({ page }) => {
    await page.goto('/chapter/00');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(5000);
    await expect(page.getByText('课程导航与岗位能力地图').first()).toBeVisible({ timeout: 10000 });
  });

  test('动画标签页显示可跳转的正文索引', async ({ page }) => {
    await page.goto('/chapter/12');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(5000);

    const animTab = page.getByText('动画').first();
    if (await animTab.isVisible({ timeout: 5000 })) {
      await animTab.click();
      await expect(page.getByText('本章动画索引')).toBeVisible();
      await expect(page.getByText('直觉机制：反馈控制闭环')).toBeVisible();
    }
  });

  test('正文动画进入视口播放且 SVG 非空', async ({ page }) => {
    await page.goto('/chapter/12');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(5000);

    const animation = page.locator('#upkie-animation-12-intuition');
    await animation.scrollIntoViewIfNeeded();
    await expect(animation).toBeVisible();
    await expect(animation).toHaveAttribute('data-playing', 'true');
    const screenshot = await animation.getByTestId('mechanism-scene').screenshot();
    expect(screenshot.byteLength).toBeGreaterThan(1000);
  });

  test('移动端显示课程和正文，不出现宽度阻断或横向溢出', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/chapter/12');
    await page.waitForLoadState('networkidle');
    await expect(page.getByText('屏幕宽度不足')).toHaveCount(0);
    await expect(page.getByText('反馈控制与闭环直觉').first()).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });

  test('减少动态效果时正文动画直接显示静态帧', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/chapter/12');
    await page.waitForLoadState('networkidle');
    const animation = page.locator('#upkie-animation-12-intuition');
    await animation.scrollIntoViewIfNeeded();
    await expect(animation).toHaveAttribute('data-motion', 'reduced');
    await expect(animation).toHaveAttribute('data-playing', 'false');
  });

  test('环境中诊断端点返回内容', async ({ page }) => {
    const resp = await page.request.get('/api/health');
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data).toHaveProperty('python');
    expect(data).toHaveProperty('mujoco');
    expect(['ready', 'degraded']).toContain(data.status);
  });
});
