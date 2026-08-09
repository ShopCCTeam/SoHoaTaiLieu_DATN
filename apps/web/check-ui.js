const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  const consoleErrors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  const routes = [
    '/dashboard',
    '/documents',
    '/documents/upload',
    '/documents/doc_01',
    '/documents/doc_02/review',
    '/search?q=nghi+hoc',
    '/chat',
    '/admin/users',
    '/admin/models',
    '/login'
  ];

  console.log('--- STARTING UI & CONSOLE CHECK ---');

  for (const route of routes) {
    try {
      const response = await page.goto(`http://localhost:3000${route}`, { waitUntil: 'networkidle' });
      const status = response ? response.status() : 'No response';
      console.log(`Route [${route}] -> Status: ${status}`);
    } catch (err) {
      console.error(`Error navigating to [${route}]:`, err.message);
    }
  }

  console.log('\n--- CONSOLE ERRORS DETECTED ---');
  if (consoleErrors.length === 0) {
    console.log('✅ 0 Console errors detected across all routes!');
  } else {
    consoleErrors.forEach((err, idx) => {
      console.log(`❌ Error ${idx + 1}: ${err}`);
    });
  }

  await browser.close();
})();
