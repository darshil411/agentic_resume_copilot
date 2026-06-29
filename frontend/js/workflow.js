let pollingInterval = null;
let currentThreadId = null;
let isHitlActive = false;

/**
 * Start polling the backend graph state.
 */
function startPolling(threadId) {
    currentThreadId = threadId;
    
    // Initial fetch immediately
    pollState();
    
    // Then poll every 3 seconds
    pollingInterval = setInterval(pollState, 3000);
}

/**
 * Stop polling
 */
function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

/**
 * Poll state logic
 */
async function pollState() {
    if (!currentThreadId) return;

    try {
        const stateData = await getWorkflowState(currentThreadId);
        handleStateUpdate(stateData);
    } catch (error) {
        console.error("Polling error:", error);
        // Optionally show toast on repeated failures, but avoid spamming
    }
}

/**
 * Handle state payload from backend
 * Expected format:
 * {
 *   state: "running|interrupt|end",
 *   next_nodes: [],
 *   values: {
 *      original_resume_html: "...",
 *      optimized_resume_html: "...",
 *      interview_questions: [...],
 *      outreach_emails: [...]
 *   }
 * }
 */
function handleStateUpdate(data) {
    if (!data) return;

    const values = data.values || {};
    const stateType = data.state; // running, interrupt, end
    const nextNodes = data.next_nodes || [];

    // Render Resume State if available
    if (values.original_resume_html || values.optimized_resume_html) {
        renderResume(
            values.original_resume_html,
            values.optimized_resume_html
        );
    }

    // Render Interview Prep if available
    if (values.interview_questions && values.interview_questions.length > 0) {
        renderInterviewDeck(values.interview_questions);
    }

    // Render Outreach if available
    if (values.outreach_emails && values.outreach_emails.length > 0) {
        renderOutreachToolkit(values.outreach_emails);
    }

    // Handle Human In The Loop (HITL) Interrupt
    if (stateType === "interrupt" || nextNodes.includes("human_review")) {
        updateStateBadge("Waiting For Approval");
        
        if (!isHitlActive) {
            isHitlActive = true;
            toggleHITLControls(true);
            showToast("Action required: Please review the optimized resume.", "info");
        }
    } else if (stateType === "end" || nextNodes.length === 0) {
        updateStateBadge("Completed");
        stopPolling();
        if (isHitlActive) {
            isHitlActive = false;
            toggleHITLControls(false);
        }
    } else {
        updateStateBadge("Processing");
        isHitlActive = false;
        toggleHITLControls(false);
    }
}

// Bind HITL UI actions
document.addEventListener('DOMContentLoaded', () => {
    const btnApprove = document.getElementById('btnApprove');
    const btnRegenerate = document.getElementById('btnRegenerate');
    const feedbackInput = document.getElementById('hitlFeedback');

    if (btnApprove) {
        btnApprove.addEventListener('click', async () => {
            const feedback = feedbackInput.value || "Looks good";
            await submitHITL(feedback, "approve");
        });
    }

    if (btnRegenerate) {
        btnRegenerate.addEventListener('click', async () => {
            const feedback = feedbackInput.value;
            if (!feedback.trim()) {
                showToast("Please provide specific feedback for regeneration.", "error");
                feedbackInput.focus();
                return;
            }
            await submitHITL(feedback, "regenerate");
        });
    }
});

async function submitHITL(feedback, action) {
    if (!currentThreadId) return;
    
    // UI Feedback
    toggleHITLControls(false);
    updateStateBadge("Processing");
    showToast(`Sending ${action} command...`, "info");
    
    try {
        await approveWorkflow(currentThreadId, feedback, action);
        showToast("Workflow resumed.", "success");
        isHitlActive = false;
        
        // Restart polling if we stopped it, or just let interval catch it
        if (!pollingInterval) {
            startPolling(currentThreadId);
        }
    } catch (err) {
        showToast(`Failed to ${action}. Please try again.`, "error");
        toggleHITLControls(true); // Re-show on failure
    }
}
