// This tells React to use the cloud URL if it exists, otherwise use localhost
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
export const API_BASE = `${API_BASE_URL.replace(/\/$/, '')}/api/v1`;

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
