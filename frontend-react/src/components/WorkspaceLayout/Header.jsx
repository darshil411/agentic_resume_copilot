import React from 'react';
import { useNavigate } from 'react-router-dom';
import { LayoutDashboard } from 'lucide-react';

export default function Header() {
    const navigate = useNavigate();
    
    return (
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center z-10">
            <div className="flex items-center gap-2">
                <LayoutDashboard className="w-6 h-6 text-navy" />
                <h1 className="text-2xl font-bold text-navy">Career Copilot Workspace</h1>
            </div>
            <button 
                onClick={() => navigate('/')} 
                className="text-navy hover:text-green font-medium text-sm transition-colors"
            >
                &larr; Start New
            </button>
        </header>
    );
}
