/**
 * CONFIT Monitoring Service
 * Connects to backend observability endpoints for health and status data.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchJson(path: string) {
    const res = await fetch(`${API_BASE}${path}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        // Allow credentials if frontend and backend share a session/cookie
        credentials: 'include',
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text}`);
    }
    return res.json();
}

export async function fetchHealth() {
    return fetchJson('/api/health');
}

export async function fetchReadiness() {
    return fetchJson('/api/health/ready');
}

export async function fetchDeepHealth() {
    return fetchJson('/api/health/deep');
}

export async function fetchMetrics() {
    // Metrics endpoint is internal; frontend does not call it directly.
    // This placeholder is available for authorized admin proxy usage if needed.
    throw new Error('Metrics endpoint is internal. Use Grafana or backend proxy.');
}
