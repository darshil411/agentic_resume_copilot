import { useState, useEffect, useRef } from 'react';
import { resumeService } from '../services/resumeService';
import { workflowStream } from '../services/workflowStream';

export function useResumeTask(threadId) {
    const [task, setTask] = useState(null);
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const isMutatingRef = useRef(false);

    useEffect(() => {
        if (!threadId) return;

        setIsLoading(true);

        const unsubscribe = workflowStream.subscribe(threadId, 'task_update', (newData, err) => {
            if (err) {
                setError(err);
                setIsLoading(false);
            } else if (newData) {
                setTask(prevTask => {
                    // Prevent flashes by dropping identical payloads
                    if (
                        prevTask &&
                        prevTask.section === newData.section &&
                        prevTask.version === newData.version &&
                        prevTask.status === newData.status &&
                        prevTask.proposal === newData.proposal
                    ) {
                        return prevTask;
                    }
                    return newData;
                });
                setError(null);
                setIsLoading(false);
            }
        });

        return () => unsubscribe();
    }, [threadId]);

    const executeWithLock = async (mutationCall) => {
        if (isMutatingRef.current) return;
        isMutatingRef.current = true;
        try {
            await mutationCall();
        } finally {
            // Keep the lock for 500ms to debounce double-clicks while SSE propagates the state update
            setTimeout(() => {
                isMutatingRef.current = false;
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

    const invalidate = () => { /* No-op with SSE */ };

    return { task, error, isLoading, approve, regenerate, skip, invalidate };
}