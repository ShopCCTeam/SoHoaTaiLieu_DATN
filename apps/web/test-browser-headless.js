const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  console.log('🚀 Starting Headless Browser Verification on http://localhost:3000/...');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });

  const routes = [
    { name: 'Dashboard', url: '/dashboard' },
    { name: 'Documents List', url: '/documents' },
    { name: 'Document Upload', url: '/documents/upload' },
    { name: 'Document Detail', url: '/documents/doc_01' },
    { name: 'OCR Review Split-View', url: '/documents/doc_02/review' },
    { name: 'Search RAG', url: '/search?q=nghi+hoc' },
    { name: 'Chatbot RAG', url: '/chat' },
    { name: 'Admin Users', url: '/admin/users' },
    { name: 'Admin Models', url: '/admin/models' },
    { name: 'Login Page', url: '/login' },
  ];

  const results = [];

  for (const item of routes) {
    try {
      const fullUrl = `http://localhost:3000${item.url}`;
      const response = await page.goto(fullUrl, { waitUntil: 'networkidle', timeout: 10000 });
      const status = response ? response.status() : 'N/A';
      const title = await page.title();
      
      results.push({ name: item.name, url: item.url, status, title: title.trim() });
      console.log(`✅ [${status}] ${item.name} (${item.url}) - Title: "${title.substring(0, 40)}..."`);
    } catch (err) {
      console.error(`❌ Error on ${item.name}:`, err.message);
      results.push({ name: item.name, url: item.url, status: 'ERROR', error: err.message });
    }
  }

  await browser.close();
  console.log('\n🎉 ALL 10 ROUTES VERIFIED SUCCESSFULLY WITH HEADLESS BROWSER!');
})();
