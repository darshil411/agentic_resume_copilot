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
    }
}

/**
 * Normalize interview questions from backend format (List[str]) to card objects.
 * Backend stores raw strings; the UI needs {question, answer, category} objects.
 */
function normalizeInterviewQuestions(raw) {
    if (!raw || raw.length === 0) return [];
    return raw.map((item, idx) => {
        if (typeof item === 'string') {
            return { question: item, answer: '', category: `Q${idx + 1}` };
        }
        // Already an object (future-proof)
        return {
            question: item.question || item,
            answer: item.answer || item.suggested_answer || '',
            category: item.category || `Q${idx + 1}`
        };
    });
}

/**
 * Normalize outreach emails from backend format (List[str]) to card objects.
 * Backend stores raw strings; the UI needs {type, subject, body} objects.
 */
function normalizeOutreachEmails(coldEmails, referrals, followups) {
    const result = [];
    (coldEmails || []).forEach(t => {
        if (typeof t === 'string') result.push({ type: 'Cold Email', subject: 'Application – [Role]', body: t });
        else result.push({ type: t.type || 'Cold Email', subject: t.subject || '', body: t.body || t });
    });
    (referrals || []).forEach(t => {
        if (typeof t === 'string') result.push({ type: 'Referral Request', subject: 'Referral – [Company]', body: t });
        else result.push({ type: t.type || 'Referral Request', subject: t.subject || '', body: t.body || t });
    });
    (followups || []).forEach(t => {
        if (typeof t === 'string') result.push({ type: 'Follow-Up', subject: 'Following Up – [Role]', body: t });
        else result.push({ type: t.type || 'Follow-Up', subject: t.subject || '', body: t.body || t });
    });
    return result;
}

/**
 * Build a simple HTML representation of a StructuredResume dict for display.
 */
function buildResumeHtml(resumeData) {
    if (!resumeData || typeof resumeData !== 'object') return null;
    const name = resumeData.name || resumeData.full_name || '';
    const summary = resumeData.summary || '';
    const skills = (resumeData.skills || []).join(', ');
    const experience = (resumeData.experience || []).map(e => {
        const title = e.title || e.role || '';
        const company = e.company || '';
        const desc = (e.description || e.responsibilities || []).join(' ');
        return `<div class="mb-3"><strong>${title}</strong>${company ? ` at ${company}` : ''}<p class="text-sm text-gray-600 mt-1">${desc}</p></div>`;
    }).join('');

    return `
        <h2 class="text-lg font-bold mb-1">${name}</h2>
        ${summary ? `<p class="text-sm text-gray-700 mb-3">${summary}</p>` : ''}
        ${skills ? `<div class="mb-3"><h4 class="text-xs font-bold text-gray-500 uppercase mb-1">Skills</h4><p class="text-sm">${skills}</p></div>` : ''}
        ${experience ? `<div class="mb-3"><h4 class="text-xs font-bold text-gray-500 uppercase mb-1">Experience</h4>${experience}</div>` : ''}
    `;
}

/**
 * Handle state payload from backend.
 * Backend response shape (from routes.py):
 * {
 *   state: "running" | "interrupt" | "end",
 *   next_nodes: [...],
 *   values: {
 *     original_resume: {...},       // StructuredResume dict
 *     optimized_resume: {...},      // StructuredResume dict
 *     interview_questions: [...],   // List[str]
 *     cold_emails: [...],           // List[str]
 *     referral_templates: [...],
 *     followup_templates: [...],
 *     workflow_logs: [...],
 *     errors: [...]
 *   }
 * }
 */
function handleStateUpdate(data) {
    if (!data) return;

    const values = data.values || {};
    const stateType = data.state;           // "running" | "interrupt" | "end"
    const nextNodes = data.next_nodes || [];

    // Log any backend errors to console for debugging
    if (values.errors && values.errors.length > 0) {
        console.warn("Backend errors:", values.errors);
    }

    // ── Error state (graph crashed in background) ──────────────────────────
    if (stateType === "error") {
        const msg = data.error_message || "An error occurred in the AI pipeline.";
        updateStateBadge("Error");
        stopPolling();
        showToast("Pipeline error: " + msg, "error");
        console.error("Graph error:", msg);
        return;
    }

    // ── Resume panels ──────────────────────────────────────────────────────
    const originalHtml = buildResumeHtml(values.original_resume);
    const optimizedHtml = buildResumeHtml(values.optimized_resume);
    if (originalHtml || optimizedHtml) {
        renderResume(originalHtml, optimizedHtml);
    }

    // ── Interview Prep ─────────────────────────────────────────────────────
    const rawQuestions = values.interview_questions || [];
    if (rawQuestions.length > 0) {
        const normalized = normalizeInterviewQuestions(rawQuestions);
        renderInterviewDeck(normalized);
    }

    // ── Outreach Toolkit ───────────────────────────────────────────────────
    const coldEmails = values.cold_emails || [];
    const referrals = values.referral_templates || [];
    const followups = values.followup_templates || [];
    if (coldEmails.length > 0 || referrals.length > 0 || followups.length > 0) {
        const normalized = normalizeOutreachEmails(coldEmails, referrals, followups);
        renderOutreachToolkit(normalized);
    }

    // ── HITL / State badge ─────────────────────────────────────────────────
    if (stateType === "interrupt" || nextNodes.some(n => n.includes("approval") || n.includes("human"))) {
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

// ── HITL UI bindings ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const btnApprove = document.getElementById('btnApprove');
    const btnRegenerate = document.getElementById('btnRegenerate');
    const feedbackInput = document.getElementById('hitlFeedback');

    if (btnApprove) {
        btnApprove.addEventListener('click', async () => {
            const feedback = feedbackInput ? feedbackInput.value || "Looks good" : "Looks good";
            await submitHITL(feedback, "approve");
        });
    }

    if (btnRegenerate) {
        btnRegenerate.addEventListener('click', async () => {
            const feedback = feedbackInput ? feedbackInput.value : '';
            if (!feedback || !feedback.trim()) {
                showToast("Please provide specific feedback for regeneration.", "error");
                if (feedbackInput) feedbackInput.focus();
                return;
            }
            await submitHITL(feedback, "regenerate");
        });
    }
});

async function submitHITL(feedback, action) {
    if (!currentThreadId) return;
    
    toggleHITLControls(false);
    updateStateBadge("Processing");
    showToast(`Sending ${action} command...`, "info");
    
    try {
        await approveWorkflow(currentThreadId, feedback, action);
        showToast("Workflow resumed.", "success");
        isHitlActive = false;
        
        // Restart polling if it was stopped
        if (!pollingInterval) {
            startPolling(currentThreadId);
        }
    } catch (err) {
        console.error("HITL submit error:", err);
        showToast(`Failed to ${action}. Please try again.`, "error");
        toggleHITLControls(true);
    }
}
