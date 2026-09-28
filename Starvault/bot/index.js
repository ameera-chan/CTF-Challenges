const express = require("express");
const puppeteer = require("puppeteer");
const fsSync = require("fs");
const fs = require("fs/promises");
const os = require("os");
const path = require("path");

const app = express();
app.use(express.json());

const PORT = 3000;
const APP_HOST = process.env.APP_HOST || "web:5000";
const BROWSER_PATH = process.env.PUPPETEER_EXECUTABLE_PATH || process.env.PUPPETEER_EXEC_PATH;
const PROFILE_PREFIX = path.join(os.tmpdir(), "starvault-curator-");

function readSecret(name) {
    if (process.env[name]) {
        return process.env[name];
    }

    const filePath = process.env[`${name}_FILE`];
    if (filePath) {
        return fsSync.readFileSync(filePath, "utf8").trim();
    }

    return "";
}

const BOT_TOKEN = readSecret("BOT_TOKEN");

if (!BOT_TOKEN) {
    throw new Error("BOT_TOKEN must be set");
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function launchBrowser(profileDir) {
    return puppeteer.launch({
        headless: "new",
        executablePath: BROWSER_PATH,
        userDataDir: profileDir,
        args: [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-background-networking",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-gpu",
            "--disable-sync",
            "--disable-translate",
            "--mute-audio",
            "--no-first-run",
            "--js-flags=--noexpose_wasm,--jitless",
        ],
    });
}

async function visitPlate(pathname) {
    const baseUrl = `http://${APP_HOST}`;
    const appHostname = new URL(baseUrl).hostname;
    let browser;
    let profileDir;

    try {
        profileDir = await fs.mkdtemp(PROFILE_PREFIX);
        browser = await launchBrowser(profileDir);
        const page = await browser.newPage();
        page.setDefaultNavigationTimeout(15000);
        page.setDefaultTimeout(15000);

        await page.goto(baseUrl, {
            waitUntil: "networkidle2",
            timeout: 15000,
        });
        await page.setCookie({
            name: "starvault_admin",
            value: BOT_TOKEN,
            domain: appHostname,
            path: "/",
            httpOnly: true,
            sameSite: "Lax",
        });

        await page.goto(`${baseUrl}${pathname}`, {
            waitUntil: "networkidle2",
            timeout: 15000,
        });

        await sleep(8000);
    } finally {
        if (browser) {
            await browser.close().catch(() => {});
        }
        if (profileDir) {
            await fs.rm(profileDir, { recursive: true, force: true }).catch(() => {});
        }
    }
}

app.post("/visit", async (request, response) => {
    const suppliedToken = request.get("x-bot-token");
    const { path: pathname } = request.body || {};

    if (suppliedToken !== BOT_TOKEN) {
        return response.status(403).json({ error: "Forbidden" });
    }

    if (typeof pathname !== "string" || !/^\/view\/[0-9a-f-]+\/$/.test(pathname)) {
        return response.status(400).json({ error: "Bad path" });
    }

    visitPlate(pathname).catch(() => {});
    return response.json({ success: true });
});

app.get("/health", (_request, response) => {
    response.json({ status: "ok" });
});

app.listen(PORT, "0.0.0.0");
