import { fetchJson } from './apiClient';

export const interviewService = {
    /**
     * @param {string} threadId 
     * @returns {Promise<import('../models/dtos').InterviewDeckDTO>}
     */
    async getInterviewDeck(threadId) {
        return await fetchJson(`/interview/${threadId}`);
    }
};
