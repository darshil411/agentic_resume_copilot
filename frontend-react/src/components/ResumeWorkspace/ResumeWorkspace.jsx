import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useResumeTask } from '../../hooks/useResumeTask';
import { WorkflowStatus } from '../../models/enums';
import { ResumePaneSkeleton } from '../common/SkeletonLoaders';
import { Check, RotateCcw, User, Briefcase, Code, BookOpen, Award } from 'lucide-react';
import { useWorkflowStatus } from '../../hooks/useWorkflowStatus';
// ---------------------------------------------------------------------------
// OriginalResumePanel — fetches and displays structured resume in a flex card
// ---------------------------------------------------------------------------
function OriginalResumePanel({ threadId }) {
    const [resume, setResume] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let mounted = true;
        const poll = async () => {
            try {
                const res = await fetch(`/api/v1/original-resume/${threadId}`);
                if (res.ok) {
                    const data = await res.json();
                    if (mounted) setResume(data);
                }
            } catch (_) {}
            finally { if (mounted) setLoading(false); }
        };
        poll();
        const interval = setInterval(poll, 4000);
        return () => { mounted = false; clearInterval(interval); };
    }, [threadId]);

    const renderSkills = (skills) => {
        if (!skills) return null;
        const allSkills = [
            ...(skills.languages || []),
            ...(skills.frameworks || []),
            ...(skills.tools || []),
            ...(skills.databases || []),
            ...(skills.concepts || []),
        ];
        return (
            <div className="flex flex-wrap gap-1.5 mt-1">
                {allSkills.map((s, i) => (
                    <span key={i} className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded-full border border-blue-100">{s}</span>
                ))}
            </div>
        );
    };

    if (loading && !resume) {
        return (
            <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm flex-shrink-0 w-full animate-pulse">
                <div className="h-5 bg-gray-200 rounded w-1/2 mb-3" />
                <div className="h-3 bg-gray-100 rounded w-3/4 mb-2" />
                <div className="h-3 bg-gray-100 rounded w-2/3 mb-2" />
                <div className="h-3 bg-gray-100 rounded w-full" />
            </div>
        );
    }

    if (!resume) return null;

    return (
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden flex-shrink-0 w-full">
            {/* Header band */}
            <div className="bg-gradient-to-r from-navy to-blue-700 p-5 text-white">
                <div className="flex items-center gap-3 mb-1">
                    <div className="bg-white/20 rounded-full p-2">
                        <User className="w-5 h-5" />
                    </div>
                    <div>
                        <h3 className="font-bold text-lg leading-tight">{resume.name || 'Your Resume'}</h3>
                        <p className="text-blue-100 text-xs">{[resume.email, resume.phone, resume.city].filter(Boolean).join(' · ')}</p>
                    </div>
                </div>
                {(resume.linkedin || resume.github) && (
                    <p className="text-blue-100 text-xs mt-1">
                        {[resume.linkedin, resume.github, resume.portfolio].filter(Boolean).join(' · ')}
                    </p>
                )}
            </div>

            <div className="p-5 space-y-4 overflow-y-auto max-h-[calc(100vh-260px)]">
                {/* Summary */}
                {resume.summary && (
                    <section>
                        <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                            <BookOpen className="w-3.5 h-3.5" /> Summary
                        </h4>
                        <p className="text-gray-700 text-sm leading-relaxed">{resume.summary}</p>
                    </section>
                )}

                {/* Skills */}
                {resume.skills && (
                    <section>
                        <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                            <Code className="w-3.5 h-3.5" /> Skills
                        </h4>
                        {renderSkills(resume.skills)}
                    </section>
                )}

                {/* Experience */}
                {resume.experience?.length > 0 && (
                    <section>
                        <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                            <Briefcase className="w-3.5 h-3.5" /> Experience
                        </h4>
                        <div className="space-y-3">
                            {resume.experience.map((exp, i) => (
                                <div key={i} className="border-l-2 border-blue-200 pl-3">
                                    <p className="font-semibold text-gray-800 text-sm">{exp.role}</p>
                                    <p className="text-xs text-gray-500">{exp.company}{exp.duration ? ` · ${exp.duration}` : ''}</p>
                                    <ul className="mt-1 space-y-0.5">
                                        {(exp.bullets || []).map((b, j) => (
                                            <li key={j} className="text-xs text-gray-600 flex gap-1.5">
                                                <span className="text-blue-400 mt-0.5 flex-shrink-0">•</span>
                                                <span>{b}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                {/* Projects */}
                {resume.projects?.length > 0 && (
                    <section>
                        <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                            <Code className="w-3.5 h-3.5" /> Projects
                        </h4>
                        <div className="space-y-2">
                            {resume.projects.map((proj, i) => (
                                <div key={i} className="bg-gray-50 rounded-lg p-2.5 border border-gray-100">
                                    <p className="font-semibold text-gray-800 text-sm">{proj.title}</p>
                                    <p className="text-xs text-gray-600 mt-0.5">{proj.description}</p>
                                    {proj.tech_stack?.length > 0 && (
                                        <div className="flex flex-wrap gap-1 mt-1.5">
                                            {proj.tech_stack.map((t, j) => (
                                                <span key={j} className="px-1.5 py-0.5 bg-white text-gray-600 text-xs rounded border border-gray-200">{t}</span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                {/* Education */}
                {resume.education?.length > 0 && (
                    <section>
                        <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                            <Award className="w-3.5 h-3.5" /> Education
                        </h4>
                        {resume.education.map((edu, i) => (
                            <div key={i} className="border-l-2 border-blue-200 pl-3">
                                <p className="font-semibold text-gray-800 text-sm">{edu.degree}</p>
                                <p className="text-xs text-gray-500">{edu.college}{edu.year ? ` · ${edu.year}` : ''}{edu.cgpa ? ` · CGPA: ${edu.cgpa}` : ''}</p>
                            </div>
                        ))}
                    </section>
                )}

                {/* Certifications */}
                {resume.certifications?.length > 0 && (
                    <section>
                        <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5">Certifications</h4>
                        <ul className="space-y-0.5">
                            {resume.certifications.map((c, i) => (
                                <li key={i} className="text-xs text-gray-700 flex gap-1.5">
                                    <span className="text-green-500">✓</span> {c}
                                </li>
                            ))}
                        </ul>
                    </section>
                )}
            </div>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Main ResumeWorkspace
// ---------------------------------------------------------------------------
export default function ResumeWorkspace() {
    const { threadId } = useParams();
    const navigate = useNavigate();
    const { task, isLoading, error, approve, regenerate, skip } = useResumeTask(threadId, 3000);
    
    const [feedback, setFeedback] = useState('');
    const [isOptimistic, setIsOptimistic] = useState(false);
    const [localError, setLocalError] = useState(null);
    
    const { data, workflow: workflowAlias } = useWorkflowStatus(threadId);
    const workflow = data || workflowAlias;

    // Automatically clear the loading skeleton and errors when the backend sends the next section
    useEffect(() => {
        setIsOptimistic(false);
        setLocalError(null);
    }, [task?.section, task?.version]);

    if (isLoading && !task) {
        return (
            <div className="flex gap-6">
                <div className="w-80 flex-shrink-0"><OriginalResumePanel threadId={threadId} /></div>
                <div className="flex-1"><ResumePaneSkeleton /></div>
            </div>
        );
    }

    if (error) {
        return <div className="text-red-600">Error loading task: {error.message}</div>;
    }

    // Layout wrapper: original resume on left, optimization panel on right
    const Layout = ({ children }) => (
        <div className="flex gap-6 items-start min-h-0">
            <div className="w-80 flex-shrink-0 sticky top-0">
                <OriginalResumePanel threadId={threadId} />
                {/* Add this inside your ResumeWorkspace sidebar/panel area */}
                <div className="bg-white rounded-xl border border-slate-200 p-4 mt-4 shadow-sm">
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                        Workflow Timeline
                    </h3>
                    <div className="space-y-2">
                        {workflow?.workflow_logs?.length > 0 ? (
                            workflow.workflow_logs.map((log, index) => (
                                <div key={index} className="flex items-start gap-2 text-sm text-slate-600">
                                    <span className="text-emerald-500 font-bold">✓</span>
                                    <span className="leading-snug">{log}</span>
                                </div>
                            ))
                        ) : (
                            <div className="text-sm text-slate-400 italic">Initializing engines...</div>
                        )}
                        
                        {/* Blinking indicator for the active task */}
                        {workflow?.overall_status === "PROCESSING" && (
                            <div className="flex items-start gap-2 text-sm text-blue-500 font-medium animate-pulse mt-2">
                                <span>⟳</span>
                                <span>Optimizing sections...</span>
                            </div>
                        )}
                        {workflow?.overall_status === "ACTION_REQUIRED" && (
                            <div className="flex items-start gap-2 text-sm text-amber-500 font-medium mt-2">
                                <span>⚠</span>
                                <span>Awaiting Human Review</span>
                            </div>
                        )}
                    </div>
                </div>
            </div>
            <div className="flex-1 min-w-0">{children}</div>
        </div>
    );

    if (!task || task.status === WorkflowStatus.PROCESSING) {
        return (
            <Layout>
                <div className="flex flex-col items-center justify-center h-64 text-center space-y-4 bg-white rounded-xl border border-gray-200 p-8">
                    <div className="relative">
                        <div className="animate-spin rounded-full h-14 w-14 border-4 border-gray-100 border-t-navy" />
                        <div className="absolute inset-0 flex items-center justify-center">
                            <div className="w-6 h-6 bg-navy rounded-full animate-pulse" />
                        </div>
                    </div>
                    <h2 className="text-xl font-bold text-navy">AI is Optimizing Your Resume...</h2>
                    <p className="text-gray-500 text-sm">
                        Currently processing the <span className="font-semibold text-navy capitalize">{task?.section || 'next'}</span> section.
                    </p>
                </div>
            </Layout>
        );
    }

    // Show the optimistic UI skeleton instantly when a button is clicked
    if (isOptimistic) {
        return (
            <Layout>
                <ResumePaneSkeleton />
            </Layout>
        );
    }

    if (task.status === WorkflowStatus.ACTION_REQUIRED) {
        const handleApprove = async () => {
            setIsOptimistic(true);
            setLocalError(null);
            try {
                await approve(task.task_id, task.version, feedback);
                setFeedback('');
            } catch (err) {
                setIsOptimistic(false);
                setLocalError("Network error: Failed to approve. Please try again.");
            }
        };
        const handleRegenerate = async () => {
            setIsOptimistic(true);
            setLocalError(null);
            try {
                await regenerate(task.task_id, task.version, feedback);
                setFeedback('');
            } catch (err) {
                setIsOptimistic(false);
                setLocalError("Network error: Failed to regenerate. Please try again.");
            }
        };
        const handleSkip = async () => {
            setIsOptimistic(true);
            setLocalError(null);
            try {
                await skip(task.task_id, task.version);
                setFeedback('');
            } catch (err) {
                setIsOptimistic(false);
                setLocalError("Network error: Failed to skip. Please try again.");
            }
        };

        return (
            <Layout>
                <div className="space-y-4">
                    {/* Display error message if the API fails */}
                    {localError && (
                        <div className="bg-red-50 text-red-600 p-3 rounded-lg border border-red-200 text-sm font-medium">
                            {localError}
                        </div>
                    )}
                    {/* Section header */}
                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
                        <div className="flex items-center gap-3 mb-1">
                            <div className="px-3 py-1 bg-amber-50 text-amber-700 text-xs font-bold uppercase rounded-full border border-amber-200">
                                Review Required
                            </div>
                            <h2 className="text-xl font-bold text-navy capitalize">{task.section} Optimization</h2>
                        </div>
                        <p className="text-gray-500 text-sm">Review the AI's proposed changes below and approve or request a revision.</p>
                    </div>

                    {/* Before / After comparison */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <div className="bg-gray-50 rounded-xl border border-gray-200 p-4">
                            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Original</h3>
                            <pre className="whitespace-pre-wrap font-sans text-gray-700 text-sm leading-relaxed">
                                {typeof task.original === 'string' ? task.original : JSON.stringify(task.original, null, 2)}
                            </pre>
                        </div>
                        <div className="bg-blue-50 rounded-xl border border-blue-200 p-4">
                            <h3 className="text-xs font-bold text-blue-600 uppercase tracking-wider mb-3">✨ AI Proposed</h3>
                            <pre className="whitespace-pre-wrap font-sans text-navy text-sm leading-relaxed">
                                {typeof task.proposal === 'string' ? task.proposal : JSON.stringify(task.proposal, null, 2)}
                            </pre>
                        </div>
                    </div>

                    {/* AI Reasoning */}
                    {task.optimization_notes && (
                        <div className="bg-green-50 rounded-xl border border-green-100 p-4">
                            <h3 className="text-xs font-bold text-green-700 uppercase tracking-wider mb-1">AI Reasoning</h3>
                            <p className="text-sm text-green-800">{task.optimization_notes}</p>
                        </div>
                    )}

                    {/* Actions */}
                    <div className="bg-white rounded-xl border border-gray-200 p-5">
                        <label className="block text-sm font-medium text-gray-700 mb-2">Optional Feedback for AI</label>
                        <textarea
                            value={feedback}
                            onChange={(e) => setFeedback(e.target.value)}
                            placeholder="E.g., Make it sound more technical, focus on leadership..."
                            className="w-full border border-gray-300 rounded-lg p-3 focus:ring-navy focus:border-navy text-sm resize-none"
                            rows="2"
                        />
                        <div className="flex gap-3 mt-3">
                            <button
                                onClick={handleSkip}
                                disabled={isOptimistic}
                                className="px-4 py-2.5 border border-gray-300 text-gray-500 rounded-lg font-medium hover:bg-gray-100 transition-colors disabled:opacity-50"
                            >
                                Skip
                            </button>
                            <button
                                onClick={handleRegenerate}
                                disabled={isOptimistic}
                                className="flex-1 py-2.5 px-4 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                            >
                                <RotateCcw className="w-4 h-4" /> Try Again
                            </button>
                            <button
                                onClick={handleApprove}
                                disabled={isOptimistic}
                                className="flex-1 py-2.5 px-4 bg-navy text-white rounded-lg font-medium hover:bg-blue-800 flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                            >
                                <Check className="w-4 h-4" /> Approve & Continue
                            </button>
                        </div>
                    </div>
                </div>
            </Layout>
        );
    }

    if (task.status === WorkflowStatus.COMPLETED || task.status === WorkflowStatus.READY) {
        return (
            <Layout>
                <div className="flex flex-col items-center justify-center h-64 text-center space-y-4 bg-white rounded-xl border border-gray-200 p-8">
                    <div className="bg-green-100 p-4 rounded-full">
                        <Check className="w-8 h-8 text-green-600" />
                    </div>
                    <h2 className="text-2xl font-bold text-navy">Resume Optimization Complete!</h2>
                    <p className="text-gray-500 max-w-md text-sm">Your resume has been fully optimized. Check the Export Hub to download it.</p>
                    <button
                        onClick={() => navigate(`/workspace/${threadId}/export`)}
                        className="mt-2 py-2.5 px-8 bg-navy text-white rounded-lg font-medium hover:bg-blue-800 transition-colors"
                    >
                        Go to Export Hub
                    </button>
                </div>
            </Layout>
        );
    }

    // Handle Workflow Failure state to prevent White Screen of Death
    if (task.status === WorkflowStatus.FAILED) {
        return (
            <Layout>
                <div className="flex flex-col items-center justify-center h-64 text-center space-y-4 bg-white rounded-xl border border-red-200 p-8">
                    <div className="bg-red-100 p-4 rounded-full text-red-600 font-bold text-xl">
                        ⚠️
                    </div>
                    <h2 className="text-2xl font-bold text-red-700">Workflow Processing Failed</h2>
                    <p className="text-gray-500 max-w-md text-sm">
                        The background optimization engine encountered an compilation or API execution failure.
                    </p>
                    <button
                        onClick={() => navigate('/')}
                        className="mt-2 py-2.5 px-8 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 transition-colors"
                    >
                        Return to Portal & Start Over
                    </button>
                </div>
            </Layout>
        );
    }

    return null;
}