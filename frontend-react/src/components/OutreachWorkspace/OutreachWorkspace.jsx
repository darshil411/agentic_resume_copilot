import React from 'react';
import { useParams } from 'react-router-dom';
import { useOutreachData } from '../../hooks/useOutreachData';
import { WorkflowStatus } from '../../models/enums';
import { CardSkeleton } from '../common/SkeletonLoaders';
import { Copy } from 'lucide-react';

export default function OutreachWorkspace() {
    const { threadId } = useParams();
    const { data, isLoading, error } = useOutreachData(threadId, 5000);

    const handleCopy = (text) => {
        navigator.clipboard.writeText(text);
        alert("Copied to clipboard!");
    };

    if (isLoading && !data) {
        return (
            <div className="space-y-4 max-w-5xl">
                <h2 className="text-2xl font-bold text-navy mb-6">Outreach Toolkit</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <CardSkeleton />
                    <CardSkeleton />
                </div>
            </div>
        );
    }

    if (error) {
        return <div className="text-red-600">Error loading outreach toolkit: {error.message}</div>;
    }

    if (!data || data.status === WorkflowStatus.PROCESSING) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-navy"></div>
                <h2 className="text-xl font-bold text-navy">Drafting Outreach Materials...</h2>
                <p className="text-gray-500">Creating tailored cold emails and referral requests.</p>
            </div>
        );
    }

    const renderCard = (card, idx) => (
        <div key={idx} className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm flex flex-col h-full">
            <div className="flex justify-between items-start mb-4">
                <span className="inline-block px-3 py-1 bg-green-50 text-green-700 text-xs font-bold uppercase rounded-full tracking-wider">
                    {card.type}
                </span>
                <button 
                    onClick={() => handleCopy(card.body)}
                    className="p-2 text-gray-400 hover:text-navy hover:bg-gray-50 rounded-md transition-colors"
                    title="Copy to clipboard"
                >
                    <Copy className="w-4 h-4" />
                </button>
            </div>
            {card.subject && (
                <div className="mb-4 pb-4 border-b border-gray-100">
                    <span className="text-xs font-bold text-gray-400 uppercase mr-2">Subject:</span>
                    <span className="font-semibold text-gray-800">{card.subject}</span>
                </div>
            )}
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-100 flex-1 overflow-y-auto">
                <pre className="text-gray-700 text-sm whitespace-pre-wrap font-sans">{card.body}</pre>
            </div>
        </div>
    );

    return (
        <div className="max-w-6xl space-y-8">
            <h2 className="text-2xl font-bold text-navy">Outreach Toolkit</h2>
            
            {data.cold_emails.length === 0 && data.referrals.length === 0 && data.followups.length === 0 ? (
                <p className="text-gray-500">No outreach templates generated yet.</p>
            ) : (
                <div className="space-y-8">
                    {data.cold_emails.length > 0 && (
                        <section>
                            <h3 className="text-xl font-bold text-gray-800 mb-4">Cold Emails</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {data.cold_emails.map((card, idx) => renderCard(card, idx))}
                            </div>
                        </section>
                    )}
                    {data.referrals.length > 0 && (
                        <section>
                            <h3 className="text-xl font-bold text-gray-800 mb-4">Referral Requests</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {data.referrals.map((card, idx) => renderCard(card, idx))}
                            </div>
                        </section>
                    )}
                    {data.followups.length > 0 && (
                        <section>
                            <h3 className="text-xl font-bold text-gray-800 mb-4">Follow-Ups</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {data.followups.map((card, idx) => renderCard(card, idx))}
                            </div>
                        </section>
                    )}
                </div>
            )}
        </div>
    );
}
