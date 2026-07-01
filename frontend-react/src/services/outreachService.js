import { fetchJson } from './apiClient';

export const outreachService = {
    /**
     * @param {string} threadId 
     * @returns {Promise<import('../models/dtos').OutreachWorkspaceDTO>}
     */
    async getOutreachWorkspace(threadId) {
        return await fetchJson(`/outreach/${threadId}`);
    }
};
