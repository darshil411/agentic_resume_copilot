import { fetchJson } from './apiClient';

export const exportService = {
    /**
     * @param {string} threadId 
     * @returns {Promise<{resume_pdf: string, interview_pdf: string, outreach_zip: string}>}
     */
    async getExportReadiness(threadId) {
        return await fetchJson(`/exports/${threadId}`);
    }
};
