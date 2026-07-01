import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useResumeTask } from '../../hooks/useResumeTask';
import { WorkflowStatus } from '../../models/enums';
import { ResumePaneSkeleton } from '../common/SkeletonLoaders';
import { Check, RotateCcw } from 'lucide-react';

export default function ResumeWorkspace() {
    const { threadId } = useParams();
    const { task, isLoading, error, approve, regenerate } = useResumeTask(threadId, 3000);
    const [feedback, setFeedback] = useState('');
    const [actionLoading, setActionLoading] = useState(false);

    if (isLoading && !task) {
        return <ResumePaneSkeleton />;
    }

    if (error) {
        return <div className="text-red-600">Error loading task: {error.message}</div>;
    }

    if (!task || task.status === WorkflowStatus.PROCESSING) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-navy"></div>
                <h2 className="text-xl font-bold text-navy">AI is Optimizing Your Resume...</h2>
                <p className="text-gray-500">Currently processing the {task?.section || 'next'} section.</p>
            </div>
        );
    }

    if (task.status === WorkflowStatus.ACTION_REQUIRED) {
        const handleApprove = async () => {
            setActionLoading(true);
            try {
                await approve(task.task_id, task.version, feedback);
                setFeedback('');
            } catch (err) {
                alert("Action failed: " + err.message);
            } finally {
                setActionLoading(false);
            }
        };

        const handleRegenerate = async () => {
            setActionLoading(true);
            try {
                await regenerate(task.task_id, task.version, feedback);
                setFeedback('');
            } catch (err) {
                alert("Action failed: " + err.message);
            } finally {
                setActionLoading(false);
            }
        };

        return (
            <div className="space-y-6 max-w-4xl">
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                    <h2 className="text-2xl font-bold text-navy mb-2 capitalize">{task.section} Optimization</h2>
                    <p className="text-gray-600 mb-6">Review the AI's proposed changes for this section.</p>

                    <div className="grid grid-cols-2 gap-6 mb-6">
                        <div className="bg-gray-50 p-4 rounded-lg border border-gray-100">
                            <h3 className="text-sm font-bold text-gray-500 uppercase mb-2 tracking-wider">Original</h3>
                            <pre className="whitespace-pre-wrap font-sans text-gray-800 text-sm">
                                {typeof task.original === 'string' ? task.original : JSON.stringify(task.original, null, 2)}
                            </pre>
                        </div>
                        <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
                            <h3 className="text-sm font-bold text-navy uppercase mb-2 tracking-wider">Proposed</h3>
                            <pre className="whitespace-pre-wrap font-sans text-navy text-sm">
                                {typeof task.proposal === 'string' ? task.proposal : JSON.stringify(task.proposal, null, 2)}
                            </pre>
                        </div>
                    </div>

                    {task.optimization_notes && (
                        <div className="bg-green-50 p-4 rounded-lg border border-green-100 mb-6">
                            <h3 className="text-sm font-bold text-green-800 mb-1">AI Reasoning</h3>
                            <p className="text-sm text-green-700">{task.optimization_notes}</p>
                        </div>
                    )}

                    <div className="border-t border-gray-200 pt-6">
                        <label className="block text-sm font-medium text-gray-700 mb-2">Optional Feedback for AI</label>
                        <textarea 
                            value={feedback}
                            onChange={(e) => setFeedback(e.target.value)}
                            placeholder="E.g., Make it sound more technical, focus on leadership..."
                            className="w-full border border-gray-300 rounded-lg p-3 focus:ring-navy focus:border-navy"
                            rows="2"
                        />
                        <div className="flex gap-4 mt-4">
                            <button 
                                onClick={handleRegenerate}
                                disabled={actionLoading}
                                className="flex-1 py-2 px-4 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 flex items-center justify-center gap-2"
                            >
                                <RotateCcw className="w-4 h-4" /> Try Again
                            </button>
                            <button 
                                onClick={handleApprove}
                                disabled={actionLoading}
                                className="flex-1 py-2 px-4 bg-navy text-white rounded-lg font-medium hover:bg-blue-800 flex items-center justify-center gap-2"
                            >
                                <Check className="w-4 h-4" /> Approve & Continue
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    if (task.status === WorkflowStatus.COMPLETED || task.status === WorkflowStatus.READY) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
                <div className="bg-green-100 p-4 rounded-full">
                    <Check className="w-8 h-8 text-green-600" />
                </div>
                <h2 className="text-2xl font-bold text-navy">Resume Optimization Complete!</h2>
                <p className="text-gray-500 max-w-md">Your resume has been fully optimized. Check the Export Hub to download it.</p>
            </div>
        );
    }

    return null;
}
