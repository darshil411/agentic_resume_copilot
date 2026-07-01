import { fetchJson } from './apiClient';

export const workflowService = {
    /**
     * @param {File} resumeFile 
     * @param {string} jobDescription 
     * @returns {Promise<{thread_id: string}>}
     */
    async startWorkflow(resumeFile, jobDescription) {
        const formData = new FormData();
        formData.append('resume', resumeFile);
        formData.append('job_description', jobDescription);

        return await fetchJson('/workflow/start', {
            method: 'POST',
            body: formData
        });
    },

    /**
     * @param {string} threadId 
     * @returns {Promise<import('../models/dtos').WorkflowMetadataDTO>}
     */
    async getWorkflowStatus(threadId) {
        return await fetchJson(`/workflow/${threadId}`);
    }
};
