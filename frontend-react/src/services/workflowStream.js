class WorkflowStreamManager {
    constructor() {
        this.streams = {}; // threadId -> { eventSource, listeners, lastData }
    }

    subscribe(threadId, eventType, callback) {
        if (!threadId) return () => {};

        if (!this.streams[threadId]) {
            const es = new EventSource(`/api/v1/workflow/stream/${threadId}`);
            this.streams[threadId] = {
                eventSource: es,
                listeners: {
                    workflow_update: new Set(),
                    task_update: new Set(),
                    interview_update: new Set(),
                    outreach_update: new Set()
                },
                lastData: {} 
            };

            const handleEvent = (type) => (e) => {
                try {
                    const data = JSON.parse(e.data);
                    this.streams[threadId].lastData[type] = data;
                    this.streams[threadId].listeners[type].forEach(cb => cb(data, null));
                } catch (err) {
                    console.error(`Error parsing SSE data for ${type}:`, err);
                    this.streams[threadId].listeners[type].forEach(cb => cb(null, err));
                }
            };

            es.addEventListener('workflow_update', handleEvent('workflow_update'));
            es.addEventListener('task_update', handleEvent('task_update'));
            es.addEventListener('interview_update', handleEvent('interview_update'));
            es.addEventListener('outreach_update', handleEvent('outreach_update'));
            
            es.onerror = (err) => {
                console.error(`SSE Error for thread ${threadId}:`, err);
                // The browser will automatically attempt to reconnect.
                // We could notify listeners of a connection drop if we wanted, but 
                // native reconnect handles recovery.
            };
        }

        const stream = this.streams[threadId];
        if (!stream.listeners[eventType]) stream.listeners[eventType] = new Set();
        stream.listeners[eventType].add(callback);

        // Immediate callback with cached data if available so new hooks get state instantly
        if (stream.lastData[eventType]) {
            callback(stream.lastData[eventType], null);
        }

        return () => {
            const currentStream = this.streams[threadId];
            if (!currentStream) return;
            
            if (currentStream.listeners[eventType]) {
                currentStream.listeners[eventType].delete(callback);
            }
            
            // Cleanup if no listeners remain for this thread
            let hasListeners = false;
            Object.values(currentStream.listeners).forEach(set => {
                if (set.size > 0) hasListeners = true;
            });
            
            if (!hasListeners) {
                currentStream.eventSource.close();
                delete this.streams[threadId];
            }
        };
    }
}

export const workflowStream = new WorkflowStreamManager();
