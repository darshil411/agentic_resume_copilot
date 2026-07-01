const API_BASE = 'http://127.0.0.1:8000/api/v1';

export class ApiError extends Error {
    constructor(message, status) {
        super(message);
        this.status = status;
    }
}

export async function fetchJson(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        if (!response.ok) {
            const errorText = await response.text();
            throw new ApiError(`API Error: ${response.status} - ${errorText}`, response.status);
        }
        return await response.json();
    } catch (err) {
        console.error(`[API FETCH ERROR] ${endpoint}`, err);
        throw err;
    }
}
