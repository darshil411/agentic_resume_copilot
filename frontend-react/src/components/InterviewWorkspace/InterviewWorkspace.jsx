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
                <h2 className="text-2xl font-bold text-navy mb-6">Interview Prep Deck</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <CardSkeleton />
                    <CardSkeleton />
                </div>
            </div>
        );
    }

    if (error) {
        return <div className="text-red-600">Error loading interview deck: {error.message}</div>;
    }

    if (!data || data.status === WorkflowStatus.PROCESSING) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-navy"></div>
                <h2 className="text-xl font-bold text-navy">Generating Interview Strategy...</h2>
                <p className="text-gray-500">Compiling questions based on your resume and job description.</p>
            </div>
        );
    }

    return (
        <div className="max-w-5xl space-y-6">
            <h2 className="text-2xl font-bold text-navy">Interview Prep Deck</h2>
            
            {data.questions.length === 0 ? (
                <p className="text-gray-500">No questions generated yet.</p>
            ) : (
                <div className="space-y-6">
                    {data.questions.map((q, idx) => (
                        <div key={idx} className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
                            <span className="inline-block px-3 py-1 bg-blue-50 text-blue-700 text-xs font-bold uppercase rounded-full mb-3 tracking-wider">
                                {q.category}
                            </span>
                            <h3 className="text-lg font-bold text-gray-900 mb-3">{q.question}</h3>
                            <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
                                <h4 className="text-xs font-bold text-gray-500 uppercase mb-2">Suggested Answer Strategy</h4>
                                <p className="text-gray-700 text-sm">{q.answer || 'Answer not provided by AI.'}</p>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
