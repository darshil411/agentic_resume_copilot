import { fetchJson } from './apiClient';

export const resumeService = {
    /**
     * @param {string} threadId 
     * @returns {Promise<import('../models/dtos').ReviewTaskDTO>}
     */
    async getCurrentTask(threadId) {
        return await fetchJson(`/resume/task/current/${threadId}`);
    },

    /**
     * @param {string} threadId 
     * @param {string} taskId 
     * @param {number} version 
     * @param {string} feedback 
     */
    async approveTask(threadId, taskId, version, feedback = "") {
        return await fetchJson(`/resume/task/approve/${threadId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: taskId, version, feedback })
        });
    },

    /**
     * @param {string} threadId 
     * @param {string} taskId 
     * @param {number} version 
     * @param {string} feedback 
     */
    async regenerateTask(threadId, taskId, version, feedback) {
        return await fetchJson(`/resume/task/regenerate/${threadId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: taskId, version, feedback })
        });
    }
};
