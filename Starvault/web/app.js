import crypto from "crypto";
import cookieParser from "cookie-parser";
import express from "express";
import fs from "fs";
import { JSDOM } from "jsdom";
import createDOMPurify from "dompurify";

const app = express();
const window = new JSDOM("").window;
const DOMPurify = createDOMPurify(window);

function readSecret(name) {
    const direct = process.env[name];
    if (direct) {
        return direct;
    }

    const filePath = process.env[`${name}_FILE`];
    if (filePath) {
        return fs.readFileSync(filePath, "utf8").trim();
    }

    return "";
}

const PORT = 5000;
const BOT_HOST = process.env.BOT_HOST || "bot:3000";
const BOT_TOKEN = readSecret("BOT_TOKEN") || crypto.randomBytes(24).toString("hex");
const FLAG = process.env.FLAG || "ICTF26{this_is_not_the_flag}";
const transmissions = new Map();

app.use(cookieParser());
app.use(express.urlencoded({ extended: false, limit: "12kb" }));
app.use("/static", express.static("public"));

app.use((request, _response, next) => {
    for (const key of Object.keys(request.query)) {
        const value = request.query[key];
        delete request.query[key];
        request.query[key.toLowerCase()] = value;
    }
    next();
});

app.use((_request, response, next) => {
    response.setHeader(
        "Content-Security-Policy",
        [
            "default-src 'self'",
            "script-src 'none'",
            "style-src 'self' 'unsafe-inline' http: https:",
            "img-src 'self' data: http: https:",
            "font-src 'self'",
            "object-src 'none'",
            "base-uri 'none'",
            "frame-ancestors 'none'",
            "form-action 'self'",
        ].join("; ")
    );
    response.setHeader("X-Content-Type-Options", "nosniff");
    response.setHeader("Referrer-Policy", "no-referrer");
    response.setHeader("Cache-Control", "no-store");
    next();
});

function makeId() {
    return crypto.randomUUID();
}

function sanitizeSignalStamp(value) {
    const loud = String(value || "").slice(0, 420).toUpperCase();
    const filtered = loud.replace(/[^A-Z0-9 .:<=>?@()_-]/g, "");
    return DOMPurify.sanitize(filtered);
}

function isAdmin(request) {
    return request.cookies.starvault_admin === BOT_TOKEN;
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function dashboardMessage(request) {
    if (request.query.sent === "1") {
        return "Submitted! The curator bot will review this record soon.";
    }
    if (request.query.error) {
        return String(request.query.error);
    }
    return "";
}

function renderRecordList(items, activeId = "") {
    if (!items.length) {
        return '<li class="empty-line">Archive is currently empty.</li>';
    }

    return items.map((transmission) => {
        const active = transmission.id === activeId ? " active" : "";
        return `
                    <li class="record-item${active}">
                        <a href="/view/${transmission.id}/">
                            <div class="record-name">${escapeHtml(transmission.title)}</div>
                        </a>
                    </li>`;
    }).join("");
}

function renderIndexPage({ recentTransmissions, message }) {
    return `<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Station Records Archive</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="header-center">station records archive // cold storage</div>
        </header>

        <main class="main-content">
            <aside class="sidebar">
                <h2 class="section-title">Records</h2>
                <ul class="record-list" id="recordList">
${renderRecordList(recentTransmissions)}
                </ul>
                <div class="sidebar-actions">
                    <form method="get" action="/">
                        <button type="submit" id="createRecordBtn" class="primary-action">Create Record</button>
                    </form>
                </div>
            </aside>

            <section class="content">
                <h2 class="section-title" id="contentSectionTitle">Create Record</h2>
                <div class="record-display">
                    ${message ? `<p class="flag-context">${escapeHtml(message)}</p>` : ""}

                    <form method="post" action="/create" id="createRecordForm" class="form-stack">
                        <label for="recordCreateTitle">Record Title / ID</label>
                        <input id="recordCreateTitle" name="title" type="text" maxlength="48" placeholder="SEC-LOG-4091" required>

                        <label for="recordCreateContent">Body</label>
                        <textarea id="recordCreateContent" name="stamp" rows="8" maxlength="420" placeholder="Insert sensor data, network logs, or observational reports here..." required></textarea>

                        <div class="record-actions">
                            <button type="submit" id="saveRecordBtn">Save Record</button>
                        </div>
                    </form>

                    <div class="diagnostics">
                        <span>COLD STORAGE</span>
                    </div>
                </div>
            </section>
        </main>

        <footer class="footer">
            <span>terminal locked</span>
            <span>provided by central archival node v4.1 build 99x2/omega</span>
        </footer>
    </div>
</body>
</html>`;
}

function renderTransmissionPage({ transmission, admin, flag }) {
    const clearance = admin
        ? `<section id="captain-clearance" class="clearance-panel hidden" aria-label="Captain Clearance">
                            <span>Captain Clearance</span>
                            <input class="clearance-seal" type="hidden" data-seal="${escapeHtml(flag)}">
                        </section>`
        : '<p class="empty-state">Captain Clearance is only visible to the station curator.</p>';

    return `<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Starvault :: ${transmission.stamp}</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="header-center">station records archive // cold storage</div>
        </header>

        <main class="main-content">
            <aside class="sidebar">
                <h2 class="section-title">Records</h2>
                <ul class="record-list" id="recordList">
${renderRecordList([transmission], transmission.id)}
                </ul>
                <div class="sidebar-actions">
                    <form method="get" action="/">
                        <button type="submit" id="createRecordBtn" class="primary-action">Create Record</button>
                    </form>
                </div>
            </aside>

            <section class="content">
                <h2 class="section-title" id="contentSectionTitle">Record Detail</h2>
                <article class="record-display">
                    <div class="record-header">
                        <span class="record-title">${escapeHtml(transmission.title)}</span>
                    </div>

                    <div class="record-body">${escapeHtml(transmission.rawStamp)}</div>

                    ${clearance}

                    <div class="record-actions">
                        <form method="post" action="/report/${transmission.id}">
                            <button id="submitToCuratorBtn" type="submit" data-action="report">Submit To Curator</button>
                        </form>
                        <form method="get" action="/">
                            <button type="submit" id="backToHomeBtn">Back To Home</button>
                        </form>
                    </div>

                    <div class="diagnostics">
                        <span>COLD STORAGE</span>
                    </div>
                </article>
            </section>
        </main>

        <footer class="footer">
            <span>terminal locked</span>
            <span>provided by central archival node v4.1 build 99x2/omega</span>
        </footer>
    </div>
</body>
</html>`;
}

app.get("/", (request, response) => {
    response.send(renderIndexPage({
        recentTransmissions: [...transmissions.values()].slice(-8).reverse(),
        message: dashboardMessage(request),
    }));
});

app.post("/create", (request, response) => {
    const title = String(request.body.title || "").trim().slice(0, 48);
    const stamp = String(request.body.stamp || "").trim();

    if (!title || !stamp) {
        return response.redirect("/?error=Title+and+signal+stamp+are+required");
    }

    const id = makeId();
    const transmission = {
        id,
        title,
        stamp: sanitizeSignalStamp(stamp),
        rawStamp: stamp.slice(0, 420),
        createdAt: new Date().toISOString(),
    };
    transmissions.set(id, transmission);
    return response.redirect(`/view/${id}/`);
});

app.get("/view/:id/", (request, response) => {
    const transmission = transmissions.get(request.params.id);
    if (!transmission) {
        return response.status(404).send("Transmission not found");
    }

    response.send(renderTransmissionPage({
        transmission,
        admin: isAdmin(request),
        flag: FLAG,
    }));
});

app.get("/view/:id/gate", (request, response) => {
    if (!transmissions.has(request.params.id)) {
        return response.status(404).send("Transmission not found");
    }

    let target = String(request.query.to || "").trim();
    if (!target) {
        return response.status(400).send("Missing target");
    }

    if (/^https?:/i.test(target)) {
        target = target.replace(/^https?:/i, (scheme) => `${scheme}//`);
    } else {
        target = `https://${target}/vault.css`;
    }

    try {
        const parsed = new URL(target);
        if (!["http:", "https:"].includes(parsed.protocol)) {
            throw new Error("bad protocol");
        }
        if (parsed.pathname === "/") {
            parsed.pathname = "/vault.css";
        }
        return response.redirect(parsed.toString());
    } catch {
        return response.status(400).send("Bad target");
    }
});

app.post("/report/:id", async (request, response) => {
    if (!transmissions.has(request.params.id)) {
        return response.status(404).send("Transmission not found");
    }

    const botResponse = await fetch(`http://${BOT_HOST}/visit`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Bot-Token": BOT_TOKEN,
        },
        body: JSON.stringify({ path: `/view/${request.params.id}/` }),
    }).catch(() => null);

    if (!botResponse?.ok) {
        return response.redirect("/?error=Curator+bot+is+unavailable");
    }

    return response.redirect("/?sent=1");
});

app.get("/health", (_request, response) => {
    response.json({ status: "ok", transmissions: transmissions.size });
});

app.listen(PORT, "0.0.0.0", () => {
    console.log(`Starvault listening on ${PORT}`);
});
