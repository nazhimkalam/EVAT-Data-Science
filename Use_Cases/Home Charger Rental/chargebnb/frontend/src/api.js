const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8001';

async function fetchJson(url, options = {}) {
  try {
    const response = await fetch(url, options);
    const data = await response.json();

    if (!response.ok) {
      console.error(`API Error [${response.status}]:`, data);
      throw new Error(data.detail || data.message || `API request failed (${response.status})`);
    }

    return data;
  } catch (error) {
    if (error instanceof SyntaxError) {
      console.error('Failed to parse API response as JSON:', error);
      throw new Error('Invalid API response. The server may be down.');
    }
    throw error;
  }
}

export async function fetchListings(start, end) {
  const params = new URLSearchParams();
  if (start) params.append('start', start);
  if (end) params.append('end', end);
  const url = `${API_BASE}/listings?${params.toString()}`;
  return fetchJson(url);
}

export async function fetchPricing(suburb, start) {
  const params = new URLSearchParams({ suburb });
  if (start) params.append('start', start);
  const url = `${API_BASE}/pricing?${params.toString()}`;
  return fetchJson(url);
}

export async function fetchBookings() {
  const url = `${API_BASE}/bookings`;
  return fetchJson(url);
}

export async function createBooking(payload) {
  const url = `${API_BASE}/bookings`;
  return fetchJson(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}
