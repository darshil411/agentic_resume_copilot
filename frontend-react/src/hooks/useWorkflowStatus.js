import { useState, useEffect, useCallback, useRef } from 'react';
import { workflowService } from '../services/workflowService';

export function useWorkflowStatus(threadId, pollInterval = 5000) {
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const intervalRef = useRef(null);

    const fetchData = useCallback(async () => {
        if (!threadId) return;
        try {
            const result = await workflowService.getWorkflowStatus(threadId);
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
        intervalRef.current = setInterval(fetchData, pollInterval);
        return () => clearInterval(intervalRef.current);
    }, [fetchData, pollInterval]);

    const invalidate = () => fetchData();

    return { data, error, isLoading, invalidate };
}
