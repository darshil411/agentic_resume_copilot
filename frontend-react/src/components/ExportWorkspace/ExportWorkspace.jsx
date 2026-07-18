import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { exportService } from '../../services/exportService';
import { useWorkflowStatus } from '../../hooks/useWorkflowStatus'; // <-- ADD THIS LINE
import { WorkflowStatus } from '../../models/enums';
import { Download, FileText, MessageSquare, Send } from 'lucide-react';

export default function ExportWorkspace() {
    const { threadId } = useParams();
    const [status, setStatus] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    const { data: workflowMeta } = useWorkflowStatus(threadId, 5000);
    useEffect(() => {
        let interval;
        const fetchStatus = async () => {
            try {
                const res = await exportService.getExportReadiness(threadId);
                setStatus(res);
                setError(null);
            } catch (err) {
                setError(err);
            } finally {
                setIsLoading(false);
            }
        };

        fetchStatus();
        interval = setInterval(fetchStatus, 5000);
        return () => clearInterval(interval);
    }, [threadId]);

    const handleDownload = (type) => {
        window.open(`/api/v1/exports/${threadId}/${type}`, '_blank');
    };

    if (isLoading) {
        return <div className="p-8">Loading export status...</div>;
    }

    if (error) {
        return <div className="p-8 text-red-600">Error: {error.message}</div>;
    }

    const cards = [
        {
            id: 'resume',
            title: 'Optimized Resume',
            desc: 'ATS-friendly PDF tailored to the JD',
            icon: FileText,
            ready: status?.resume_pdf === WorkflowStatus.READY
        },
        {
            id: 'interview',
            title: 'Interview Strategy Deck',
            desc: 'PDF containing QA and company research',
            icon: MessageSquare,
            ready: status?.interview_pdf === WorkflowStatus.READY
        },
        {
            id: 'outreach',
            title: 'Outreach Toolkit',
            desc: 'ZIP of cold emails and templates',
            icon: Send,
            ready: status?.outreach_zip === WorkflowStatus.READY
        }
    ];

    const origReport = workflowMeta?.ats_report;
    const optReport = workflowMeta?.optimized_ats_report;
    const origMissing = origReport?.missing_skills || [];
    const optMissing = optReport?.missing_skills || [];
    const resolvedSkills = origMissing.filter(s => !optMissing.includes(s));
    const newlyMissingSkills = optMissing.filter(s => !origMissing.includes(s));

    return (
        <div className="max-w-4xl space-y-6 pb-12">
            <h2 className="text-2xl font-bold text-navy mb-2">Export Hub</h2>

            {/* --- ATS Dashboard Panel --- */}
            {origReport && optReport ? (
                <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm mb-8">
                    <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-6">Optimization Impact</h3>
                    <div className="ats-dashboard-panel">
                        <div className="ats-score-card original">
                            <span className="ats-label original">Original Match</span>
                            <div className="ats-score original">{origReport.score || 0}%</div>
                        </div>

                        <div className="ats-arrow-bridge">
                            <div className={`ats-arrow-icon ${optReport.score >= origReport.score ? 'positive' : 'negative'}`}>➡️</div>
                            <div className={`ats-badge ${optReport.score >= origReport.score ? 'positive' : 'negative'}`}>
                                {optReport.score >= origReport.score 
                                    ? `+${optReport.score - origReport.score} Points` 
                                    : `${optReport.score - origReport.score} Points`}
                            </div>
                        </div>

                        <div className="ats-score-card optimized">
                            <span className="ats-label optimized">Optimized Match</span>
                            <div className="ats-score optimized">{optReport.score || 0}%</div>
                        </div>
                    </div>

                    {(resolvedSkills.length > 0 || newlyMissingSkills.length > 0) && (
                        <div className="flex flex-col md:flex-row gap-4 mt-6">
                            {resolvedSkills.length > 0 && (
                                <div className="improvement-breakdown positive flex-1">
                                    <h4>✓ Targeted Skills Added</h4>
                                    <p>{resolvedSkills.join(', ')}</p>
                                </div>
                            )}
                            {newlyMissingSkills.length > 0 && (
                                <div className="improvement-breakdown negative flex-1">
                                    <h4>⚠️ Dropped Keywords</h4>
                                    <p>{newlyMissingSkills.join(', ')}</p>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            ) : (
                <div className="ats-calculating-msg mb-8">
                    <div className="animate-pulse flex items-center justify-center gap-3">
                        <div className="h-4 w-4 rounded-full bg-blue-400"></div>
                        Generating final competitive analysis metrics...
                    </div>
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8 border-t border-gray-200 pt-8">
                {cards.map((card) => {
                    const Icon = card.icon;
                    return (
                        <div key={card.id} className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm flex flex-col items-center text-center">
                            <div className="bg-blue-50 p-4 rounded-full mb-4">
                                <Icon className="w-8 h-8 text-navy" />
                            </div>
                            <h3 className="text-lg font-bold text-gray-900 mb-2">{card.title}</h3>
                            <p className="text-gray-500 text-sm mb-6 flex-1">{card.desc}</p>
                            
                            <button
                                onClick={() => handleDownload(card.id)}
                                disabled={!card.ready}
                                className={`w-full py-2 px-4 rounded-lg font-medium flex items-center justify-center gap-2 transition-colors ${
                                    card.ready 
                                    ? 'bg-navy text-white hover:bg-blue-800' 
                                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                }`}
                            >
                                <Download className="w-4 h-4" />
                                {card.ready ? 'Download' : 'Processing...'}
                            </button>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
