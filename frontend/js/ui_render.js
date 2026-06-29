/**
 * Show a custom Toast notification.
 * @param {string} message 
 * @param {string} type - 'success', 'error', 'info'
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    // Trigger reflow to animate
    void toast.offsetWidth;
    toast.classList.add('show');

    // Remove after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Render the resume content (Original vs Optimized)
 */
function renderResume(originalHtml, optimizedHtml) {
    const origContainer = document.getElementById('resumeOriginalContent');
    const optContainer = document.getElementById('resumeOptimizedContent');

    if (origContainer && originalHtml) {
        origContainer.innerHTML = originalHtml;
    }
    if (optContainer && optimizedHtml) {
        // Find modified text and wrap in ai-highlight (Basic heuristic, backend usually does this)
        // Assuming backend sends it pre-formatted with highlight spans if necessary, 
        // or we just inject it directly.
        optContainer.innerHTML = optimizedHtml;
    }
}

/**
 * Show or hide HITL controls for approval.
 */
function toggleHITLControls(show) {
    const controls = document.getElementById('hitlControls');
    if (!controls) return;
    
    if (show) {
        controls.classList.remove('translate-y-full');
    } else {
        controls.classList.add('translate-y-full');
    }
}

/**
 * Render the Interview Prep Deck with 3D Flip Cards
 */
let currentCardIndex = 0;
let interviewCardsData = [];

function renderInterviewDeck(questions) {
    const container = document.getElementById('interviewDeckContainer');
    const controls = document.getElementById('interviewControls');
    
    if (!container || !questions || questions.length === 0) return;

    interviewCardsData = questions;
    currentCardIndex = 0;
    
    // Clear skeletons
    container.innerHTML = '';
    
    if (controls) {
        controls.classList.remove('hidden');
        document.getElementById('cardCounter').textContent = `1 / ${questions.length}`;
        document.getElementById('btnPrevCard').disabled = true;
        document.getElementById('btnNextCard').disabled = questions.length <= 1;
    }

    // Render the first card
    _renderActiveCard();
}

function _renderActiveCard() {
    const container = document.getElementById('interviewDeckContainer');
    const data = interviewCardsData[currentCardIndex];
    if (!data) return;

    const cardHtml = `
        <div class="flip-card w-full max-w-sm h-64 cursor-pointer" onclick="this.classList.toggle('flipped')">
            <div class="flip-card-inner">
                <!-- Front -->
                <div class="flip-card-front p-6 flex flex-col justify-center items-center">
                    <span class="text-xs font-bold text-green uppercase tracking-wider mb-2">${data.category || 'Question'}</span>
                    <h3 class="text-lg font-semibold text-navy text-center leading-snug">${data.question}</h3>
                    <p class="text-gray-400 text-xs mt-4">Click to flip</p>
                </div>
                <!-- Back -->
                <div class="flip-card-back p-6 flex flex-col justify-start items-start overflow-y-auto">
                    <h3 class="text-sm font-bold text-navy mb-2">Suggested Answer</h3>
                    <p class="text-sm text-gray-700 leading-relaxed">${data.answer || 'Provide your answer here based on the optimized resume.'}</p>
                    
                    <button class="mt-auto self-end text-navy hover:text-green" onclick="copyText(event, \`${(data.answer || '').replace(/`/g, "\\`")}\`)">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                    </button>
                </div>
            </div>
        </div>
    `;
    container.innerHTML = cardHtml;
}

// Bind deck navigation
document.addEventListener('DOMContentLoaded', () => {
    const btnPrev = document.getElementById('btnPrevCard');
    const btnNext = document.getElementById('btnNextCard');

    if (btnPrev && btnNext) {
        btnPrev.addEventListener('click', () => {
            if (currentCardIndex > 0) {
                currentCardIndex--;
                _renderActiveCard();
                _updateDeckControls();
            }
        });
        btnNext.addEventListener('click', () => {
            if (currentCardIndex < interviewCardsData.length - 1) {
                currentCardIndex++;
                _renderActiveCard();
                _updateDeckControls();
            }
        });
    }
});

function _updateDeckControls() {
    document.getElementById('cardCounter').textContent = `${currentCardIndex + 1} / ${interviewCardsData.length}`;
    document.getElementById('btnPrevCard').disabled = currentCardIndex === 0;
    document.getElementById('btnNextCard').disabled = currentCardIndex === interviewCardsData.length - 1;
}

/**
 * Copy to clipboard utility
 */
function copyText(e, text) {
    e.stopPropagation(); // prevent card flip
    navigator.clipboard.writeText(text).then(() => {
        const btn = e.currentTarget;
        const icon = btn.innerHTML;
        // Morph to checkmark
        btn.innerHTML = `<svg class="w-5 h-5 text-green" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>`;
        btn.classList.add('text-green');
        
        setTimeout(() => {
            btn.innerHTML = icon;
            btn.classList.remove('text-green');
        }, 2000);
    });
}

/**
 * Render Outreach Masonry Grid
 */
function renderOutreachToolkit(emails) {
    const container = document.getElementById('outreachGrid');
    if (!container || !emails || emails.length === 0) return;

    container.innerHTML = '';
    
    emails.forEach(email => {
        // Parse template variables like [Company Name] into span pills
        const formattedBody = (email.body || '').replace(
            /\[([^\]]+)\]/g, 
            '<span class="template-pill" contenteditable="true">$1</span>'
        );

        const card = document.createElement('div');
        card.className = 'masonry-item bg-white p-5 rounded-lg border border-gray-200 shadow-custom-sm relative group';
        
        card.innerHTML = `
            <div class="flex justify-between items-start mb-3">
                <span class="text-xs font-bold text-navy bg-blue-50 px-2 py-1 rounded tracking-wider">${email.type || 'Email'}</span>
                <button class="text-gray-400 hover:text-green opacity-0 group-hover:opacity-100 transition-opacity" onclick="copyText(event, this.parentElement.nextElementSibling.nextElementSibling.innerText)">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                </button>
            </div>
            <h4 class="font-semibold text-sm mb-2 text-black">${email.subject || 'Subject'}</h4>
            <div class="text-sm text-gray-700 leading-relaxed space-y-2 whitespace-pre-wrap">${formattedBody}</div>
        `;
        container.appendChild(card);
    });
}

/**
 * Update State Badge
 */
function updateStateBadge(stateName) {
    const badge = document.getElementById('resumeStateBadge');
    const statusInd = document.getElementById('statusIndicator');
    if (!badge) return;

    // Remove old classes
    badge.className = 'px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider';

    if (stateName.toLowerCase().includes('wait') || stateName.toLowerCase().includes('interrupt')) {
        badge.classList.add('bg-yellow-100', 'text-yellow-700', 'animate-pulse');
        badge.textContent = 'Waiting for Approval';
        statusInd.innerHTML = 'Status: <span class="font-medium text-yellow-600">Action Required</span>';
    } else if (stateName.toLowerCase().includes('end') || stateName.toLowerCase().includes('complete')) {
        badge.classList.add('bg-green-100', 'text-green-700');
        badge.textContent = 'Export Ready';
        statusInd.innerHTML = 'Status: <span class="font-medium text-green-600">Workflow Complete</span>';
    } else {
        badge.classList.add('bg-blue-100', 'text-blue-700');
        badge.textContent = 'Processing';
        statusInd.innerHTML = 'Status: <span class="font-medium text-blue-600">Running graph...</span>';
    }
}
