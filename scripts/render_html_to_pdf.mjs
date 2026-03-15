import { chromium } from 'playwright';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [, , inputHtml, outputPdf, screenshotPath = ''] = process.argv;
if (!inputHtml || !outputPdf) {
  console.error('Usage: node scripts/render_html_to_pdf.mjs <input-html> <output-pdf> [screenshot-png]');
  process.exit(1);
}

const executablePath = process.env.CHROME_PATH || '/usr/bin/google-chrome';
const browser = await chromium.launch({
  executablePath,
  headless: true,
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--allow-file-access-from-files'],
});

try {
  const page = await browser.newPage();
  await page.goto(pathToFileURL(path.resolve(inputHtml)).toString(), { waitUntil: 'networkidle' });
  await page.waitForFunction(() => window.__renderDone === true, { timeout: 20000 });
  await page.pdf({
    path: outputPdf,
    format: 'A4',
    printBackground: true,
    margin: { top: '12mm', right: '12mm', bottom: '12mm', left: '12mm' },
  });
  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true });
  }
} finally {
  await browser.close();
}
