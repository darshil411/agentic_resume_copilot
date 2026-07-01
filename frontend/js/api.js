const API_BASE = 'http://127.0.0.1:8000/api/v1';

/**
 * Start the workflow by uploading resume and JD.
 */
async function startWorkflow(pdfFile, jobDescription) {
    console.log('[API] Starting workflow with resume and job description');
    const formData = new FormData();
    formData.append('resume', pdfFile);
    formData.append('job_description', jobDescription);

    try {
        console.log(`[API] POST ${API_BASE}/workflow/start`);
        const response = await fetch(`${API_BASE}/workflow/start`, {
            method: 'POST',
            body: formData
        });

        console.log(`[API] Response status: ${response.status}`);
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`[API ERROR] HTTP ${response.status}: ${errorText}`);
            throw new Error(`API error: ${response.status}`);
        }
        const data = await response.json();
        console.log('[API] Workflow started:', data);
        return data;
    } catch (err) {
        console.error('[API FETCH ERROR]', err);
        throw err;
    }
}

/**
 * Poll the workflow state.
 */
async function getWorkflowState(threadId) {
    console.log(`[API] Calling: ${API_BASE}/workflow/${threadId}/state`);
    try {
        const response = await fetch(`${API_BASE}/workflow/${threadId}/state`);
        console.log(`[API] Response status: ${response.status}`);
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`[API ERROR] HTTP ${response.status}: ${errorText}`);
            throw new Error(`API error: ${response.status} - ${errorText}`);
        }
        const data = await response.json();
        console.log('[API] Received state data:', data);
        return data;
    } catch (err) {
        console.error('[API FETCH ERROR]', err);
        throw err;
    }
}

/**
 * Submit user feedback to resume the workflow from a breakpoint.
 * @param {string} threadId - the active thread
 * @param {string} feedback  - user's text feedback
 * @param {string} action    - "approve" or "regenerate"
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
            approved: action === 'approve'
        })
    });

    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }
    
    // FIX 3: Unfreeze the frontend polling loop immediately upon successful API response
    isHitlActive = false;
    
    return response.json();
}