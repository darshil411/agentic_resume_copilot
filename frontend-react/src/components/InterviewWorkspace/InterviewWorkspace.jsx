import React from 'react';
import { useParams } from 'react-router-dom';
import { useInterviewData } from '../../hooks/useInterviewData';
import { WorkflowStatus } from '../../models/enums';
import { CardSkeleton } from '../common/SkeletonLoaders';

export default function InterviewWorkspace() {
    const { threadId } = useParams();
    const { data, isLoading, error } = useInterviewData(threadId, 5000);

    if (isLoading && !data) {
        return (
            <div className="space-y-4 max-w-5xl">
                <h2 className="text-2xl font-bold text-navy mb-6">Interview Strategy Deck</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6"><CardSkeleton /><CardSkeleton /></div>
            </div>
        );
    }

    if (error) return <div className="text-red-600">Error loading deck: {error.message}</div>;

    if (!data || data.status === WorkflowStatus.PROCESSING) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-center space-y-4 py-20">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                <h2 className="text-xl font-bold text-navy">Running Multi-Agent Research Loops...</h2>
                <p className="text-gray-500 text-sm">Crawling systems data architectures, filtering noise, and compressing analytical signals.</p>
            </div>
        );
    }

    const confidenceColors = {
        HIGH: 'bg-green-100 text-green-800 border-green-200',
        MEDIUM: 'bg-yellow-100 text-yellow-800 border-yellow-200',
        LOW: 'bg-red-100 text-red-800 border-red-200'
    };

    return (
        <div className="max-w-5xl space-y-10 pb-10">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-100 pb-6">
                <div>
                    <h2 className="text-3xl font-extrabold text-navy tracking-tight">Interview Strategy Dossier</h2>
                    <p className="text-gray-500 mt-2 text-sm">Surgically matching your technical projects against verified engineering parameters.</p>
                </div>
                <div className="flex flex-col items-start md:items-end gap-2">
                    <span className={`px-3 py-1 border rounded-full text-xs font-bold uppercase tracking-wider ${confidenceColors[data.confidence_score] || 'bg-gray-100'}`}>
                        Grounding: {data.confidence_score}
                    </span>
                    <div className="text-xs text-gray-400">
                        Sources: {data.source_basis?.join(', ')}
                    </div>
                </div>
            </div>
            
            {/* Top Quad Layout Context Deck */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
                    <h3 className="text-sm font-bold text-gray-900 mb-4 uppercase tracking-wider text-gray-500 flex items-center gap-2">
                        <span>🏢</span> Company Intelligence Summary
                    </h3>
                    <ul className="space-y-3">
                        {data.company_intel?.map((intel, i) => (
                            <li key={i} className="text-sm text-gray-700 flex gap-2 leading-relaxed">
                                <span className="text-blue-500 font-bold">•</span> {intel}
                            </li>
                        ))}
                    </ul>
                </div>

                <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
                    <h3 className="text-sm font-bold text-gray-900 mb-4 uppercase tracking-wider text-gray-500 flex items-center gap-2">
                        <span>🗣️</span> Target Interview Loop Process
                    </h3>
                    <ul className="space-y-3">
                        {data.experiences?.map((exp, i) => (
                            <li key={i} className="text-sm text-gray-700 flex gap-2 leading-relaxed">
                                <span className="text-blue-500 font-bold">•</span> {exp}
                            </li>
                        ))}
                    </ul>
                </div>

                <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
                    <h3 className="text-sm font-bold text-gray-900 mb-4 uppercase tracking-wider text-gray-500 flex items-center gap-2">
                        <span>🔍</span> Public Forum Historic Questions
                    </h3>
                    <ul className="space-y-3">
                        {data.company_questions?.map((q, i) => (
                            <li key={i} className="text-sm text-gray-600 flex gap-2 italic leading-relaxed">
                                <span className="text-blue-400 font-serif">"</span> {q} "
                            </li>
                        ))}
                    </ul>
                </div>

                <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
                    <h3 className="text-sm font-bold text-gray-900 mb-4 uppercase tracking-wider text-gray-500 flex items-center gap-2">
                        <span>🗓️</span> Preparation Roadmap Matrix
                    </h3>
                    <ul className="space-y-3">
                        {data.roadmap?.map((step, i) => (
                            <li key={i} className="text-sm text-gray-700 flex gap-2 leading-relaxed">
                                <span className="text-blue-500 font-bold">{i+1}.</span> {step}
                            </li>
                        ))}
                    </ul>
                </div>
            </div>

            {/* Target Grounded Strategic Questions */}
            <div className="space-y-6">
                <h3 className="text-lg font-bold text-gray-900 uppercase tracking-wider text-gray-500 flex items-center gap-2">
                    <span>💡</span> Top 5 Grounded High-Probability Questions
                </h3>
                
                <div className="space-y-6">
                    {data.questions?.map((q, idx) => (
                        <div key={idx} className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm hover:border-gray-300 transition-all">
                            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                                <span className="px-2.5 py-0.5 bg-blue-50 text-blue-700 text-[11px] font-bold uppercase rounded-md tracking-wider">
                                    {q.category}
                                </span>
                                <span className="text-xs text-gray-400 font-medium">
                                    Target Focus: <strong className="text-gray-600 font-semibold">{q.project_to_highlight}</strong>
                                </span>
                            </div>
                            
                            <h4 className="text-lg font-bold text-gray-900 leading-snug">{idx + 1}. {q.question}</h4>
                            
                            <div className="mt-3 text-sm text-gray-600 leading-relaxed bg-gray-50 border border-gray-100 rounded-lg p-3">
                                <strong className="text-xs font-bold text-gray-400 uppercase tracking-wider block mb-1">Interviewer Intent:</strong>
                                {q.interviewer_intent}
                            </div>

                            {q.answer && (
                                <div className="bg-blue-50/40 rounded-lg p-4 border border-blue-100/50 mt-4">
                                    <h5 className="text-xs font-bold text-blue-600 uppercase tracking-wider mb-2">Suggested Strategy Matrix (X-Y-Z)</h5>
                                    <p className="text-gray-700 text-sm leading-relaxed whitespace-pre-wrap">{q.answer}</p>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}