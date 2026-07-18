const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..', '..');
const out = process.env.CHEMPREDICT_TEST_OUTPUT
  || path.join(root, '07_验证结果', 'browser', 'local-run');
const baseUrl = (process.env.CHEMPREDICT_BASE_URL || 'http://127.0.0.1:8788').replace(/\/$/, '');
fs.mkdirSync(out, { recursive: true });

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

(async () => {
  const launchOptions = { headless: true };
  if (process.env.CHROME_EXE) launchOptions.executablePath = process.env.CHROME_EXE;
  const browser = await chromium.launch(launchOptions);
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('console', (message) => { if (message.type() === 'error') errors.push(`console: ${message.text()}`); });
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));

  await page.goto(`${baseUrl}/index.html`, { waitUntil: 'networkidle' });
  assert((await page.title()).includes('v4.4'), 'title does not identify v4.4');
  assert(await page.locator('#system-selector option').count() === 9, 'reaction-system registry was not rendered');
  assert((await page.locator('#condition-candidate option').first().textContent()).includes('（'), 'Chinese condition term lacks annotation');
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), 'desktop horizontal overflow');
  await page.screenshot({ path: path.join(out, 'workspace-zh-desktop.png'), fullPage: true });

  await page.click('[data-language="en"]');
  const englishTerm = await page.locator('#condition-candidate option').first().textContent();
  assert(!englishTerm.includes('（'), 'English mode still contains Chinese annotation');
  assert((await page.locator('html').getAttribute('lang')) === 'en', 'document language was not switched');
  await page.screenshot({ path: path.join(out, 'workspace-en-desktop.png'), fullPage: true });

  await page.selectOption('#system-selector', 'kharasch_haloalkylation');
  assert(await page.locator('#system-boundary').isVisible(), 'evidence-only system boundary is hidden');
  assert(await page.locator('#quantitative-workspace').isHidden(), 'quantitative controls remain visible for evidence-only system');

  await page.selectOption('#system-selector', 'nhp_deoxygenative_asymmetric_cyanation');
  await page.click('[data-language="zh"]');
  await page.click('[data-mode="custom"]');
  await page.selectOption('#substituent-template', 'p_cn');
  await page.click('#custom-form button[type="submit"]');
  const resultText = await page.locator('#custom-result').innerText();
  assert(resultText.includes('D级适用域'), 'strong para EWG did not produce grade D');
  assert(resultText.includes('35'), 'strong para EWG interval was not extended to 35%');

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload({ waitUntil: 'networkidle' });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), 'mobile horizontal overflow');
  await page.screenshot({ path: path.join(out, 'workspace-zh-mobile.png'), fullPage: true });

  assert(errors.length === 0, errors.join('\n'));
  fs.writeFileSync(path.join(out, 'ui_test_result.json'), JSON.stringify({ status: 'PASS', systemCount: 9, errors }, null, 2));
  await browser.close();
  console.log('PASS: v4.4 bilingual multi-system UI');
})().catch(async (error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
});
