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
            setError(err);
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
        await fetchTask(); // invalidate cache immediately
    };

    const regenerate = async (taskId, version, feedback) => {
        await resumeService.regenerateTask(threadId, taskId, version, feedback);
        await fetchTask(); // invalidate cache immediately
    };

    const invalidate = () => fetchTask();

    return { task, error, isLoading, approve, regenerate, invalidate };
}
