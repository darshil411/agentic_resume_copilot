import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { exportService } from '../../services/exportService';
import { WorkflowStatus } from '../../models/enums';
import { Download, FileText, MessageSquare, Send } from 'lucide-react';

export default function ExportWorkspace() {
    const { threadId } = useParams();
    const [status, setStatus] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

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
        alert(`Downloading ${type}... (Not implemented in backend yet)`);
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

    return (
        <div className="max-w-4xl space-y-6">
            <h2 className="text-2xl font-bold text-navy mb-6">Export Hub</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
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
