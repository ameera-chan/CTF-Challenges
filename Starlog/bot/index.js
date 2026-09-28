const express = require('express');
const puppeteer = require('puppeteer');
const Redis = require('ioredis');

const app = express();
app.use(express.json());

const PORT = 3000;
const APP_HOST = process.env.APP_HOST || 'web:5000';
const FLAG = process.env.FLAG;
const REDIS_HOST = process.env.REDIS_HOST || 'redis';
const REDIS_PORT = parseInt(process.env.REDIS_PORT) || 6379;

const redis = new Redis({
    host: REDIS_HOST,
    port: REDIS_PORT
});

const redisBlocking = new Redis({
    host: REDIS_HOST,
    port: REDIS_PORT
});

redis.set('queued_count', 0);
redis.set('processed_count', 0);

let browser;

async function initBrowser() {
    if (!browser || !browser.isConnected()) {
        browser = await puppeteer.launch({
            headless: 'new',
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-background-networking',
                '--disable-default-apps',
                '--disable-extensions',
                '--disable-gpu',
                '--disable-sync',
                '--disable-translate',
                '--hide-scrollbars',
                '--metrics-recording-only',
                '--mute-audio',
                '--no-first-run',
                '--safebrowsing-disable-auto-update',
                '--disable-features=CrossSiteDocumentBlockingAlways,IsolateOrigins,site-per-process,CrossOriginOpenerPolicy,CrossOriginEmbedderPolicy'
            ]
        });
    }
    return browser;
}

async function visitPage(pagePath) {
    const baseUrl = `http://${APP_HOST}`;
    let page = null;
    
    try {
        browser = await initBrowser();
        page = await browser.newPage();
        
        page.setDefaultNavigationTimeout(10000);
        page.setDefaultTimeout(10000);
        
        console.log(`[Bot] Starting review`);
        
        await page.setCookie({
            name: 'admin_token',
            value: FLAG,
            domain: APP_HOST.split(':')[0],
            path: '/',
            httpOnly: false,
            sameSite: 'Lax'
        });
        
        console.log(`[Bot] Admin cookie set`);
        
        const targetUrl = pagePath.startsWith('/') 
            ? `${baseUrl}${pagePath}` 
            : `${baseUrl}/${pagePath}`;
             
        console.log(`[Bot] Visiting reported page: ${targetUrl}`);
        
        await page.goto(targetUrl, {
            waitUntil: 'networkidle2',
            timeout: 15000
        });
        
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        console.log(`[Bot] Review completed`);
        
    } catch (error) {
        console.error(`[Bot] Error during review: ${error.message}`);
    } finally {
        if (page) {
            await page.close().catch(() => {});
        }
    }
}

async function processQueue() {
    while (true) {
        try {
            const result = await redisBlocking.blpop('review_queue', 5);
            
            if (!result) {
                continue;
            }

            const pagePath = result[1];
            console.log(`[Queue] Processing: ${pagePath}`);

            await visitPage(pagePath);
            await redis.incr('processed_count');
        } catch (error) {
            console.error(`[Queue] Error: ${error.message}`);
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }
}

app.post('/visit', async (req, res) => {
    const { path } = req.body;
    
    if (!path) {
        return res.status(400).json({ error: 'Missing path parameter' });
    }
    
    if (!path.match(/^\/view\/[a-f0-9-]+(\?.*)?$/)) {
        return res.status(400).json({ error: 'Invalid path format' });
    }
    
    try {
        await redis.rpush('review_queue', path);
        await redis.incr('queued_count');
        
        console.log(`[API] Queued for review: ${path}`);
        res.json({ success: true, message: 'Report queued for review' });
    } catch (error) {
        console.error(`[API] Error queueing: ${error.message}`);
        res.status(500).json({ error: 'Failed to queue report' });
    }
});

app.get('/health', (req, res) => {
    res.json({ status: 'ok' });
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`[Server] Bot server running on port ${PORT}`);
    
    processQueue().catch(error => {
        console.error(`[Fatal] Queue processor crashed: ${error.message}`);
        process.exit(1);
    });
});

process.on('SIGTERM', async () => {
    console.log('[Shutdown] Received SIGTERM, closing...');
    if (browser) {
        await browser.close();
    }
    await redis.quit();
    process.exit(0);
});
