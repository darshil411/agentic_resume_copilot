import { useState, useEffect, useCallback, useRef } from 'react';
import { resumeService } from '../services/resumeService';

export function useResumeTask(threadId, pollInterval = 5000) {
    const [task, setTask] = useState(null);
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const intervalRef = useRef(null);

    const [isInitialLoad, setIsInitialLoad] = useState(true);
    const abortControllerRef = useRef(null);
    const isMutatingRef = useRef(false);

    const fetchTask = useCallback(async (isSilent = false) => {
        if (!threadId || isMutatingRef.current) return;

        if (abortControllerRef.current) abortControllerRef.current.abort();
        abortControllerRef.current = new AbortController();

        if (!isSilent && isInitialLoad) setIsLoading(true);

        try {
            const currentAbort = abortControllerRef.current;
            const result = await resumeService.getCurrentTask(threadId);
            
            if (currentAbort.signal.aborted) return;

            setTask(prevTask => {
                if (
                    prevTask &&
                    prevTask.section === result.section &&
                    prevTask.version === result.version &&
                    prevTask.status === result.status &&
                    prevTask.proposal === result.proposal
                ) {
                    return prevTask; // Drop identical network payloads to prevent DOM flashes
                }
                return result;
            });
            setError(null);
        } catch (err) {
            if (abortControllerRef.current?.signal.aborted) return;
            const status = err?.status;
            if (status && status >= 400 && status < 500) setError(err);
        } finally {
            if (!isSilent && !isMutatingRef.current && !abortControllerRef.current?.signal.aborted) {
                setIsLoading(false);
                setIsInitialLoad(false);
            }
        }
    }, [threadId, isInitialLoad]);

    useEffect(() => {
        fetchTask();
        intervalRef.current = setInterval(() => fetchTask(true), pollInterval);
        return () => {
            clearInterval(intervalRef.current);
            if (abortControllerRef.current) abortControllerRef.current.abort();
        };
    }, [fetchTask, pollInterval]);

    const executeWithLock = async (mutationCall) => {
        isMutatingRef.current = true;
        try {
            await mutationCall();
        } finally {
            // Give LangGraph 500ms to save the SQL checkpoint before we fetch the next state
            setTimeout(() => {
                fetchTask(true).finally(() => { isMutatingRef.current = false; });
            }, 500);
        }
    };

    const approve = async (taskId, version, feedback) => {
        await executeWithLock(() => resumeService.approveTask(threadId, taskId, version, feedback));
    };

    const regenerate = async (taskId, version, feedback) => {
        await executeWithLock(() => resumeService.regenerateTask(threadId, taskId, version, feedback));
    };

    const skip = async (taskId, version) => {
        await executeWithLock(() => resumeService.skipTask(threadId, taskId, version));
    };

    const invalidate = () => fetchTask();

    return { task, error, isLoading, approve, regenerate, skip, invalidate };
}