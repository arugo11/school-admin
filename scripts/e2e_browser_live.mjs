import { chromium } from 'playwright';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');
const baseUrl = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:4173';
const fixturePath = process.env.E2E_FIXTURE ?? path.join(repoRoot, 'data/test/confirmation_test-3.jpg');
const studentName = process.env.E2E_STUDENT_NAME ?? 'Yuna Kobayashi';
const routeTimeoutMs = Number(process.env.E2E_ROUTE_TIMEOUT_MS ?? '300000');

async function waitForPath(page, pathname) {
  await page.waitForURL((url) => url.pathname === pathname, { timeout: routeTimeoutMs });
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

try {
  await page.goto(`${baseUrl}/students`, { waitUntil: 'networkidle', timeout: 120000 });
  await page.getByRole('button', { name: new RegExp(studentName, 'i') }).click();
  await waitForPath(page, '/upload');

  await page.setInputFiles('input[type="file"]', fixturePath);
  await waitForPath(page, '/ocr-review');
  await page.getByRole('button', { name: '分析へ進む' }).waitFor({ timeout: routeTimeoutMs });
  await page.getByRole('button', { name: '分析へ進む' }).click();
  await waitForPath(page, '/analysis');

  await page.getByRole('button', { name: '宿題承認へ' }).click();
  await waitForPath(page, '/homework-review');

  const cards = page.locator('.recommendation-card.active, .recommendation-card');
  if (await cards.count()) {
    await cards.first().click();
  }
  await page.getByRole('button', { name: 'この内容で承認' }).click();
  await waitForPath(page, '/students');
  await page.getByRole('heading', { name: '生徒一覧' }).waitFor({ timeout: 60000 });

  console.log(JSON.stringify({ status: 'pass', baseUrl, fixturePath }, null, 2));
} catch (error) {
  console.error(JSON.stringify({
    status: 'fail',
    baseUrl,
    fixturePath,
    error: error instanceof Error ? error.message : String(error),
  }, null, 2));
  process.exitCode = 1;
} finally {
  await page.close();
  await browser.close();
}
