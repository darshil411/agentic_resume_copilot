let pollingInterval = null;
let currentThreadId = null;
let isHitlActive = false;

// FIX 1: Remove the hard polling freeze. The backend will now tell us the true state.
function startPolling(threadId) {
    currentThreadId = threadId;
    pollState();
    pollingInterval = setInterval(pollState, 3000); 
}

function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

async function pollState() {
    if (!currentThreadId) return;
    try {
        const stateData = await getWorkflowState(currentThreadId);
        if (!stateData) return;
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
// 2. The Corrected HITL Render Logic
// 2. The Corrected HITL Render Logic
function handleStateUpdate(stateData) {
    const values = stateData.values || {};
    const state = stateData.state;

    // FIX 2: Restore the Error Handler so the UI doesn't silently ignore crashes
    if (state === "error") {
        if (typeof updateStateBadge === "function") updateStateBadge("Error");
        stopPolling();
        showToast("Pipeline error occurred. Check backend terminal.", "error");
        return;
    }

    if (typeof updateStateBadge === "function") {
        if (state === "interrupt") updateStateBadge("Waiting For Approval");
        else if (state === "end") updateStateBadge("Completed");
        else updateStateBadge("Processing");
    }

    // A. Render Original Resume (Left Panel)
    if (values.original_resume) {
        const originalHtml = buildResumeHtml(values.original_resume);
        const originalContainer = document.getElementById("resumeOriginalContent");
        if (originalContainer) originalContainer.innerHTML = originalHtml;
    }

    // B. Handle the Interrupt (Right Panel - Proposed Changes)
    if (state === "interrupt") {
        isHitlActive = true;
        if (typeof toggleHITLControls === "function") toggleHITLControls(true);

        const proposed = values.proposed_changes || {};
        const currentSection = values.current_section || "section";

        const sectionLabel = document.getElementById("currentSectionLabel");
        if (sectionLabel) sectionLabel.innerText = `Currently Reviewing: ${currentSection}`;

        let proposalHtml = `<div class="text-gray-500 italic flex justify-center mt-10">Formatting proposal...</div>`;
        
        if (proposed.new_content) {
            proposalHtml = `
                <div class="p-4 bg-blue-50 border border-blue-200 rounded-lg shadow-sm">
                    <h3 class="text-lg font-bold text-[#0d47a1] mb-2">Proposed ${currentSection} Upgrade</h3>
                    <p class="text-xs text-gray-600 mb-4">${proposed.reasoning || "Optimized for ATS matching."}</p>
                    <div class="whitespace-pre-wrap font-mono text-sm text-black bg-white p-3 border border-gray-200 rounded">
                        ${proposed.new_content}
                    </div>
                </div>
            `;
        }
        const optimizedContainer = document.getElementById("resumeOptimizedContent");
        if (optimizedContainer) optimizedContainer.innerHTML = proposalHtml;
        
        // FIX 3: We REMOVED the "return;" statement here.
        // The script now continues downward to render your parallel branches!
    }

    // C. Graph Resumed / Committed
    if (isHitlActive && state === "running") {
        isHitlActive = false;
        if (typeof toggleHITLControls === "function") toggleHITLControls(false);
        const sectionLabel = document.getElementById("currentSectionLabel");
        if (sectionLabel) sectionLabel.innerText = "Processing Next Section...";
    }

    if (values.optimized_resume && !isHitlActive) {
        const optimizedHtml = buildResumeHtml(values.optimized_resume);
        const optimizedContainer = document.getElementById("resumeOptimizedContent");
        if (optimizedContainer) {
            optimizedContainer.innerHTML = optimizedHtml;
        }
    }

    // D. End State
    if (state === "end") {
        isHitlActive = false;
        if (typeof toggleHITLControls === "function") toggleHITLControls(false);
        const sectionLabel = document.getElementById("currentSectionLabel");
        if (sectionLabel) sectionLabel.innerText = "Final Optimized Resume";
        stopPolling();
    }
    
    // E. Interview Prep (Now successfully renders even during a resume interrupt!)
    const rawQuestions = values.interview_questions || [];
    if (rawQuestions.length > 0) {
        const normalized = normalizeInterviewQuestions(rawQuestions);
        if (typeof renderInterviewDeck === "function") renderInterviewDeck(normalized);
    }

    // F. Outreach Toolkit
    const coldEmails = values.cold_emails || [];
    const referrals = values.referral_templates || [];
    const followups = values.followup_templates || [];
    if (coldEmails.length > 0 || referrals.length > 0 || followups.length > 0) {
        const normalized = normalizeOutreachEmails(coldEmails, referrals, followups);
        if (typeof renderOutreachToolkit === "function") renderOutreachToolkit(normalized);
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
