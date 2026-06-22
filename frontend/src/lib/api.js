const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';
const REQUEST_TIMEOUT_MS = 5000;

async function fetchWithTimeout(path, options = {}) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const startedAt = performance.now();

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });

    const latency = Math.round(performance.now() - startedAt);
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.message || `Request failed with HTTP ${response.status}`);
    }

    return { data, latency };
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('Backend request timed out');
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export function fetchSuggestions(prefix) {
  return fetchWithTimeout(`/suggest?q=${encodeURIComponent(prefix)}`);
}

export function submitSearch(query) {
  return fetchWithTimeout('/search', {
    method: 'POST',
    body: JSON.stringify({ query }),
  });
}
