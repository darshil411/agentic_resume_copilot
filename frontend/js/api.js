const API_BASE = 'http://127.0.0.1:8000/api/v1';

/**
 * Start the workflow by uploading resume and JD.
 */
async function startWorkflow(pdfFile, jobDescription) {
    const formData = new FormData();
    formData.append('resume', pdfFile);
    formData.append('job_description', jobDescription);

    const response = await fetch(`${API_BASE}/workflow/start`, {
        method: 'POST',
        body: formData
    });

    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }
    return response.json();
}

/**
 * Poll the workflow state.
 */
async function getWorkflowState(threadId) {
    const response = await fetch(`${API_BASE}/workflow/${threadId}/state`);
    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }
    return response.json();
}

/**
 * Submit user feedback to resume the workflow from a breakpoint.
 */
async function approveWorkflow(threadId, feedback, action) {
    const response = await fetch(`${API_BASE}/workflow/approve`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            thread_id: threadId,
            feedback: feedback,
            action: action // "approve" or "regenerate"
        })
    });

    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }
    return response.json();
}
