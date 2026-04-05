const puppeteer = require('puppeteer-core');
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = '/home/user/Bootstrap-3d';
const PORT = 8801;
const OUT = path.join(ROOT, 'renders/viewer_screenshot.png');

function startServer() {
    return new Promise((resolve) => {
        const server = http.createServer((req, res) => {
            let filePath = path.join(ROOT, decodeURIComponent(req.url === '/' ? '/index.html' : req.url));
            fs.readFile(filePath, (err, data) => {
                if (err) { res.writeHead(404); res.end('Not found'); return; }
                const ext = path.extname(filePath);
                const types = {
                    '.html':'text/html', '.js':'application/javascript', '.mjs':'application/javascript',
                    '.css':'text/css', '.png':'image/png', '.jpg':'image/jpeg',
                    '.glb':'model/gltf-binary', '.gltf':'model/gltf+json', '.json':'application/json',
                    '.wasm':'application/wasm'
                };
                res.writeHead(200, {
                    'Content-Type': types[ext] || 'application/octet-stream',
                    'Access-Control-Allow-Origin': '*'
                });
                res.end(data);
            });
        });
        server.listen(PORT, '127.0.0.1', () => resolve(server));
    });
}

async function main() {
    const server = await startServer();
    console.log(`Server on http://127.0.0.1:${PORT}`);

    const browser = await puppeteer.launch({
        executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
        headless: 'new',
        args: [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-web-security',
            '--enable-webgl',
            '--use-gl=angle',
            '--use-angle=swiftshader',
            '--enable-unsafe-swiftshader',
        ],
        protocolTimeout: 120000,
    });

    const page = await browser.newPage();
    page.on('console', msg => console.log('PAGE:', msg.text()));
    page.on('pageerror', err => console.log('PAGE ERROR:', err.message));

    await page.setViewport({ width: 1280, height: 900 });

    const target = process.argv[2] || '/test_viewer.html';
    console.log(`Loading ${target}...`);
    try {
        await page.goto(`http://127.0.0.1:${PORT}${target}`, { waitUntil: 'load', timeout: 60000 });
    } catch(e) {
        console.log('Goto error:', e.message);
    }

    console.log('Waiting 15s for Three.js + model...');
    await new Promise(r => setTimeout(r, 15000));

    await page.screenshot({ path: OUT, fullPage: false });
    console.log(`Screenshot saved: ${OUT}`);

    await browser.close();
    server.close();
}

main().catch(e => { console.error(e); process.exit(1); });
