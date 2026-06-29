let pollingInterval = null;
let currentThreadId = null;
let isHitlActive = false;

/**
 * Start polling the backend graph state.
 */
function startPolling(threadId) {
    console.log('[INIT] Starting polling with thread ID:', threadId);
    currentThreadId = threadId;
    
    // Initial fetch immediately
    pollState();
    
    // Then poll every 3 seconds
    pollingInterval = setInterval(pollState, 3000);
    console.log('[INIT] Polling interval set (every 3s)');
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
        console.log(`[POLLING] Fetching state for thread: ${currentThreadId}`);
        const stateData = await getWorkflowState(currentThreadId);
        console.log('[POLLING] Received state data:', stateData);
        handleStateUpdate(stateData);
    } catch (error) {
        console.error("[POLLING ERROR] Failed to fetch state:", error);
        console.error("[POLLING ERROR] Thread ID:", currentThreadId);
        showToast(`API Error: ${error.message || 'Failed to connect to backend'}`, "error");
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

    // --- SKILLS ---
    let skillsList = [];
    if (resumeData.skills && typeof resumeData.skills === 'object' && !Array.isArray(resumeData.skills)) {
        skillsList = [
            ...(resumeData.skills.languages || []),
            ...(resumeData.skills.frameworks || []),
            ...(resumeData.skills.tools || []),
            ...(resumeData.skills.databases || []),
            ...(resumeData.skills.concepts || [])
        ];
    } else if (Array.isArray(resumeData.skills)) {
        skillsList = resumeData.skills;
    } else if (typeof resumeData.skills === 'string') {
        skillsList = [resumeData.skills]; // Fallback if AI returns a plain string
    }
    const skills = skillsList.join(', ');

    // --- EXPERIENCE ---
    let experience = '';
    if (Array.isArray(resumeData.experience)) {
        experience = resumeData.experience.map(e => {
            const title = e.title || e.role || '';
            const company = e.company || '';
            const duration = e.duration ? ` <span class="text-black">| ${e.duration}</span>` : '';
            // Handle bullets if they are an array or a string
            const desc = Array.isArray(e.bullets || e.description || e.responsibilities) 
                            ? (e.bullets || e.description || e.responsibilities).join(' ')
                            : (e.bullets || e.description || e.responsibilities || '');
            return `<div class="mb-3"><strong>${title}</strong>${company ? ` at ${company}` : ''}${duration}<p class="text-sm text-black mt-1">${desc}</p></div>`;
        }).join('');
    } else if (typeof resumeData.experience === 'string') {
        // Safe fallback if AI returns a plain text string
        experience = `<div class="mb-3"><p class="text-sm text-black mt-1 whitespace-pre-wrap">${resumeData.experience}</p></div>`;
    }

    // --- PROJECTS ---
    let projects = '';
    if (Array.isArray(resumeData.projects)) {
        projects = resumeData.projects.map(p => {
            const title = p.title || p.name || '';
            const tech = p.tech_stack && Array.isArray(p.tech_stack) && p.tech_stack.length > 0 ? `<span class="text-xs text-green font-bold ml-2">(${p.tech_stack.join(', ')})</span>` : '';
            const desc = p.description || '';
            return `<div class="mb-3"><strong>${title}</strong>${tech}<p class="text-sm text-black mt-1">${desc}</p></div>`;
        }).join('');
    } else if (typeof resumeData.projects === 'string') {
        // Safe fallback if AI returns a plain text string
        projects = `<div class="mb-3"><p class="text-sm text-black mt-1 whitespace-pre-wrap">${resumeData.projects}</p></div>`;
    }

    // --- EDUCATION ---
    let education = '';
    if (Array.isArray(resumeData.education)) {
        education = resumeData.education.map(ed => {
            const degree = ed.degree || '';
            const college = ed.college || ed.institution || '';
            const year = ed.year ? ` | ${ed.year}` : '';
            const cgpa = ed.cgpa ? ` (CGPA: ${ed.cgpa})` : '';
            return `<div class="mb-2"><strong>${degree}</strong><br><span class="text-sm text-black">${college}${year}${cgpa}</span></div>`;
        }).join('');
    } else if (typeof resumeData.education === 'string') {
        education = `<div class="mb-2"><span class="text-sm text-black whitespace-pre-wrap">${resumeData.education}</span></div>`;
    } else if (resumeData.education && typeof resumeData.education === 'object') {
        // Safe fallback if AI returns a single object instead of an array of objects
        const ed = resumeData.education;
        const degree = ed.degree || '';
        const college = ed.college || ed.institution || '';
        const year = ed.year ? ` | ${ed.year}` : '';
        const cgpa = ed.cgpa ? ` (CGPA: ${ed.cgpa})` : '';
        education = `<div class="mb-2"><strong>${degree}</strong><br><span class="text-sm text-black">${college}${year}${cgpa}</span></div>`;
    }

    // --- ASSEMBLE FINAL HTML ---
    return `
        <div class="bg-white text-black p-2">
            <h2 class="text-lg font-bold mb-1 text-navy">${name}</h2>
            ${summary ? `<p class="text-sm text-black mb-4 whitespace-pre-wrap">${summary}</p>` : ''}
            
            ${skills ? `<div class="mb-4"><h4 class="text-xs font-bold text-navy uppercase mb-1 border-b border-navy pb-1">Skills</h4><p class="text-sm">${skills}</p></div>` : ''}
            
            ${experience ? `<div class="mb-4"><h4 class="text-xs font-bold text-navy uppercase mb-1 border-b border-navy pb-1">Experience</h4>${experience}</div>` : ''}
            
            ${projects ? `<div class="mb-4"><h4 class="text-xs font-bold text-navy uppercase mb-1 border-b border-navy pb-1">Projects</h4>${projects}</div>` : ''}
            
            ${education ? `<div class="mb-4"><h4 class="text-xs font-bold text-navy uppercase mb-1 border-b border-navy pb-1">Education</h4>${education}</div>` : ''}
        </div>
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
    const stateType = data.state;           
    const nextNodes = data.next_nodes || [];

    if (values.errors && values.errors.length > 0) {
        console.warn("Backend errors:", values.errors);
    }

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
    let optimizedHtml = "";

    // THE FIX: Render the AI's proposed changes to the UI while waiting for user approval
    // THE FIX: Render AI proposed changes safely, even if they are JSON objects
    if (stateType === "interrupt" && values.proposed_changes) {
        const sectionName = (values.current_section || "Section").toUpperCase();
        const reasoning = values.proposed_changes.reasoning || "Optimized for ATS matching.";
        
        // Safely stringify the content if the AI returned a JSON object/array instead of a string
        let content = values.proposed_changes.new_content || "";
        if (typeof content === 'object') {
            content = JSON.stringify(content, null, 2);
        }
        
        // Safely fetch the resume preview (Subgraph state sometimes hides the original_resume)
        const resumeToPreview = values.optimized_resume || values.original_resume;
        let currentResumeHtml = resumeToPreview 
            ? buildResumeHtml(resumeToPreview) 
            : `<div class="p-4 text-gray-500 italic text-sm">Resume preview syncing...</div>`;
        
        optimizedHtml = `
            <div class="bg-blue-50 text-blue-800 p-4 mb-4 rounded-lg border border-blue-200 shadow-sm">
                <h4 class="font-bold text-sm mb-1 flex items-center gap-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    Proposed Change for ${sectionName}
                </h4>
                <p class="text-xs leading-relaxed mb-3">${reasoning}</p>
                <div class="p-3 bg-white border border-blue-100 rounded text-black whitespace-pre-wrap font-mono text-sm">${content}</div>
            </div>
            
            <div class="opacity-60 pointer-events-none border-t pt-4">
                <h3 class="text-xs font-bold text-gray-400 uppercase mb-3">Current Resume Preview</h3>
                ${currentResumeHtml}
            </div>
        `;
      } else if (values.optimized_resume) {

        optimizedHtml = buildResumeHtml(values.optimized_resume);


    } else {
        optimizedHtml = `<div class="text-gray-400 italic text-sm text-center mt-10">Optimizations will appear here once generated...</div>`;
    }

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
    if (stateType === "interrupt") {
        updateStateBadge("Waiting For Approval");
        if (!isHitlActive) {
            isHitlActive = true;
            toggleHITLControls(true);
            showToast("Action required: Please review the optimized resume.", "info");
        }
    } else if (stateType === "end") {
        updateStateBadge("Completed");
        stopPolling();
        showToast("All done! Your career copilot results are ready.", "success");
        if (isHitlActive) {
            isHitlActive = false;
            toggleHITLControls(false);
        }
    } else {
        updateStateBadge("Processing");
        if (isHitlActive) {
            isHitlActive = false;
            toggleHITLControls(false);
        }
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
