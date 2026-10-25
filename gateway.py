"""Master FastAPI gateway — mounts every studio + the Meta-Orchestrator."""
from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from meta_orchestrator.api import router as orchestrator_router
from studios.branding.router import router as branding_router
from studios.core_mesh.router import router as mesh_router
from studios.design.router import router as design_router
from studios.marketing.router import router as marketing_router

load_dotenv()

app = FastAPI(
    title="Digital Agency Factory",
    version="1.0.0",
    description="Autonomous, cloud-routed Digital Agency. CPU-only host safe.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orchestrator_router)
app.include_router(branding_router)
app.include_router(design_router)
app.include_router(marketing_router)
app.include_router(mesh_router)


@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    """Serve the Factory Command Center UI."""
    return """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Digital Agency Factory</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        brand: '#10b981', // emerald-500
                        surface: '#0f172a', // slate-900
                        panel: '#1e293b', // slate-800
                    }
                }
            }
        }
    </script>
    <style>
        body { font-family: 'Inter', system-ui, -apple-system, sans-serif; }
        .glow { box-shadow: 0 0 20px rgba(16, 185, 129, 0.2); }
        pre { white-space: pre-wrap; word-wrap: break-word; }
    </style>
</head>
<body class="bg-surface text-slate-300 min-h-screen p-4 md:p-8">

    <!-- Header -->
    <header class="max-w-6xl mx-auto mb-8 flex flex-col md:flex-row items-center justify-between">
        <div>
            <h1 class="text-3xl font-bold text-white flex items-center gap-3">
                <span class="text-brand">🏭</span> Digital Agency Factory
            </h1>
            <p class="text-slate-400 mt-1">Autonomous Swarm Orchestrator — Live API</p>
        </div>
        <div class="mt-4 md:mt-0 flex gap-3">
            <span class="px-3 py-1 bg-emerald-900/30 text-brand border border-emerald-800 rounded-full text-sm font-semibold flex items-center gap-2">
                <span class="w-2 h-2 bg-brand rounded-full animate-pulse"></span> API ONLINE
            </span>
            <a href="/docs" target="_blank" class="px-3 py-1 bg-panel hover:bg-slate-700 border border-slate-700 rounded-full text-sm font-semibold transition">
                Swagger Docs ↗
            </a>
        </div>
    </header>

    <!-- Main Grid -->
    <main class="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
        
        <!-- Left Column: System Health -->
        <div class="space-y-4 md:col-span-1">
            <div class="bg-panel p-5 rounded-xl border border-slate-700 shadow-lg">
                <h2 class="text-lg font-semibold text-white mb-4 border-b border-slate-700 pb-2">System Health</h2>
                <div class="space-y-3" id="health-checks">
                    <div class="flex justify-between items-center text-sm">
                        <span>Branding Studio</span>
                        <span class="text-slate-500" id="health-branding">Pinging...</span>
                    </div>
                    <div class="flex justify-between items-center text-sm">
                        <span>Design Studio</span>
                        <span class="text-slate-500" id="health-design">Pinging...</span>
                    </div>
                    <div class="flex justify-between items-center text-sm">
                        <span>Marketing Studio</span>
                        <span class="text-slate-500" id="health-marketing">Pinging...</span>
                    </div>
                    <div class="flex justify-between items-center text-sm">
                        <span>Core Mesh</span>
                        <span class="text-slate-500" id="health-mesh">Pinging...</span>
                    </div>
                </div>
            </div>

            <div class="bg-panel p-5 rounded-xl border border-slate-700 shadow-lg">
                <h2 class="text-lg font-semibold text-white mb-2">Environment</h2>
                <ul class="text-sm space-y-2 text-slate-400">
                    <li class="flex justify-between"><span>Host:</span> <span class="text-slate-200">Vercel Serverless</span></li>
                    <li class="flex justify-between"><span>Compute:</span> <span class="text-slate-200">CPU-Only</span></li>
                    <li class="flex justify-between"><span>Routing:</span> <span class="text-brand">Cloud API</span></li>
                </ul>
            </div>
        </div>

        <!-- Right Column: Interactive Tester -->
        <div class="md:col-span-2 space-y-4">
            <div class="bg-panel p-5 rounded-xl border border-slate-700 shadow-lg">
                <div class="flex justify-between items-center mb-4 border-b border-slate-700 pb-2">
                    <h2 class="text-lg font-semibold text-white">Full Agency Generation</h2>
                    <span class="text-xs text-slate-400">POST /studios/mesh/build</span>
                </div>
                
                <form id="mesh-form" class="space-y-4">
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-xs text-slate-400 mb-1">Company Name</label>
                            <input type="text" id="company" value="Northwind" class="w-full bg-surface border border-slate-700 rounded-lg p-2 text-white focus:outline-none focus:border-brand" required>
                        </div>
                        <div>
                            <label class="block text-xs text-slate-400 mb-1">Industry</label>
                            <input type="text" id="industry" value="Logistics" class="w-full bg-surface border border-slate-700 rounded-lg p-2 text-white focus:outline-none focus:border-brand" required>
                        </div>
                    </div>
                    <button type="submit" class="w-full bg-brand hover:bg-emerald-600 text-slate-900 font-bold py-2 rounded-lg transition glow">
                        🚀 Run Core Mesh Build
                    </button>
                </form>

                <div class="mt-4">
                    <div class="flex justify-between items-center mb-2">
                        <span class="text-xs text-slate-400">Response Output</span>
                        <button id="copy-btn" class="text-xs text-brand hover:underline">Copy JSON</button>
                    </div>
                    <pre id="output" class="bg-surface p-4 rounded-lg border border-slate-700 text-xs text-emerald-300 overflow-y-auto max-h-64 font-mono shadow-inner">Awaiting request...</pre>
                </div>
            </div>
        </div>

    </main>

    <script>
        // Health Checks
        const healthEndpoints = {
            'health-branding': '/studios/branding/health',
            'health-design': '/studios/design/health',
            'health-marketing': '/studios/marketing/health',
            'health-mesh': '/studios/mesh/status'
        };

        async function checkHealth() {
            for (const [elementId, endpoint] of Object.entries(healthEndpoints)) {
                try {
                    const res = await fetch(endpoint);
                    const el = document.getElementById(elementId);
                    if (res.ok) {
                        el.innerHTML = '<span class="text-brand font-bold">● Ready</span>';
                    } else {
                        el.innerHTML = '<span class="text-red-500 font-bold">● Error</span>';
                    }
                } catch (e) {
                    document.getElementById(elementId).innerHTML = '<span class="text-red-500">● Offline</span>';
                }
            }
        }

        // Mesh Form Submission
        document.getElementById('mesh-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = e.target.querySelector('button');
            const output = document.getElementById('output');
            
            btn.innerHTML = '⏳ Processing...';
            btn.disabled = true;
            output.textContent = 'Swarm executing... Please wait.';

            const payload = {
                company: document.getElementById('company').value,
                industry: document.getElementById('industry').value,
                values: ["reliability", "speed"],
                budget_usd: 5000
            };

            try {
                const res = await fetch('/studios/mesh/build', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                const data = await res.json();
                output.textContent = JSON.stringify(data, null, 2);
                output.className = "bg-surface p-4 rounded-lg border border-slate-700 text-xs text-emerald-300 overflow-y-auto max-h-64 font-mono shadow-inner";
            } catch (error) {
                output.textContent = "Error: " + error.message;
                output.className = "bg-red-900/20 p-4 rounded-lg border border-red-800 text-xs text-red-400 overflow-y-auto max-h-64 font-mono shadow-inner";
            } finally {
                btn.innerHTML = '🚀 Run Core Mesh Build';
                btn.disabled = false;
            }
        });

        // Copy Button
        document.getElementById('copy-btn').addEventListener('click', () => {
            const text = document.getElementById('output').textContent;
            navigator.clipboard.writeText(text);
            const btn = document.getElementById('copy-btn');
            btn.textContent = 'Copied!';
            setTimeout(() => btn.textContent = 'Copy JSON', 2000);
        });

        // Run health checks on load
        checkHealth();
    </script>
</body>
</html>
    """


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("gateway:app", host="0.0.0.0", port=8000, reload=True)
