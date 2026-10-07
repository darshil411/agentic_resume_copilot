import { useState, useEffect } from 'react';
import { workflowStream } from '../services/workflowStream';

export function useInterviewData(threadId) {
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        if (!threadId) return;

        setIsLoading(true);

        const unsubscribe = workflowStream.subscribe(threadId, 'interview_update', (newData, err) => {
            if (err) {
                setError(err);
                setIsLoading(false);
            } else if (newData) {
                setData(newData);
                setError(null);
                setIsLoading(false);
            }
        });

        return () => unsubscribe();
    }, [threadId]);

    return { data, error, isLoading };
}
