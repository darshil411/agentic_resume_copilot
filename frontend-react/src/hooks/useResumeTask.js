import { useState, useEffect, useCallback, useRef } from 'react';
import { resumeService } from '../services/resumeService';

export function useResumeTask(threadId, pollInterval = 5000) {
    const [task, setTask] = useState(null);
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const intervalRef = useRef(null);

    const fetchTask = useCallback(async () => {
        if (!threadId) return;
        try {
            const result = await resumeService.getCurrentTask(threadId);
            setTask(result);
            setError(null);
        } catch (err) {
            // Only surface hard errors (4xx client errors).
            // 5xx / network errors are transient \u2014 the resume subgraph may not have
            // started yet (interview/outreach are still running), so silently retry.
            const status = err?.status;
            const isPermanent = status && status >= 400 && status < 500;
            if (isPermanent) {
                setError(err);
            }
            // Transient errors: keep existing task data (or null) and keep polling
        } finally {
            setIsLoading(false);
        }
    }, [threadId]);

    useEffect(() => {
        fetchTask();
        intervalRef.current = setInterval(fetchTask, pollInterval);
        return () => clearInterval(intervalRef.current);
    }, [fetchTask, pollInterval]);

    const approve = async (taskId, version, feedback) => {
        await resumeService.approveTask(threadId, taskId, version, feedback);
        await fetchTask();
    };

    const regenerate = async (taskId, version, feedback) => {
        await resumeService.regenerateTask(threadId, taskId, version, feedback);
        await fetchTask();
    };

    const invalidate = () => fetchTask();

    return { task, error, isLoading, approve, regenerate, skip, invalidate };
}
