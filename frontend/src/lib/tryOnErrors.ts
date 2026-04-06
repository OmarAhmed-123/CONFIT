/**
 * Normalize try-on failures for UI (fetch, abort, backend errors).
 */

export function formatTryOnFailureMessage(err: unknown): string {
    if (err instanceof DOMException && err.name === 'AbortError') {
        return (
            'Processing timed out. Increase VITE_TRYON_TIMEOUT_MS / TRYON_REQUEST_TIMEOUT_SEC, ' +
            'or retry. On CPU, ensure TRYON_FABRIC_PHYSICS is unset or 0; MediaPipe Tasks models ' +
            'download on first API run.'
        );
    }
    if (err instanceof Error && /quality too low|could not produce an acceptable result/i.test(err.message)) {
        return err.message;
    }
    if (err instanceof TypeError && /fetch|network|failed to load/i.test(String(err.message))) {
        return 'Network error — check that the API server is running and reachable.';
    }
    if (err instanceof Error) {
        return err.message;
    }
    return String(err);
}
