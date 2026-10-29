const {defineConfig}=require('@playwright/test');
module.exports=defineConfig({
  testDir:'tests/browser',testMatch:'*.spec.cjs',workers:1,fullyParallel:false,
  timeout:45000,globalTimeout:600000,retries:0,reporter:'list',
  use:{baseURL:'http://127.0.0.1:8786',serviceWorkers:'block',viewport:{width:1280,height:800},trace:'retain-on-failure'},
  webServer:{command:`"${process.env.TEST_PYTHON||'python'}" tests/browser/server.py`,url:'http://127.0.0.1:8786/accounts/login/',reuseExistingServer:false,timeout:90000}
});
