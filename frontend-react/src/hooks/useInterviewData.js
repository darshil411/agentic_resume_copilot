import { useState, useEffect, useCallback, useRef } from 'react';
import { interviewService } from '../services/interviewService';

export function useInterviewData(threadId, pollInterval = 5000) {
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const intervalRef = useRef(null);

    const fetchData = useCallback(async () => {
        if (!threadId) return;
        try {
            const result = await interviewService.getInterviewDeck(threadId);
            setData(result);
            setError(null);
        } catch (err) {
            setError(err);
        } finally {
            setIsLoading(false);
        }
    }, [threadId]);

    useEffect(() => {
        fetchData();
        // Stop polling if data is ready
        if (data?.status === 'READY' || data?.status === 'FAILED') {
            clearInterval(intervalRef.current);
            return;
        }
        intervalRef.current = setInterval(fetchData, pollInterval);
        return () => clearInterval(intervalRef.current);
    }, [fetchData, pollInterval, data?.status]);

    return { data, error, isLoading };
}
