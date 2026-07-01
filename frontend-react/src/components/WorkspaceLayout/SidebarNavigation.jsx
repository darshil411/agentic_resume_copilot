import React from 'react';
import { NavLink } from 'react-router-dom';
import { useWorkflowStatus } from '../../hooks/useWorkflowStatus';
import { WorkflowStatus } from '../../models/enums';
import { FileText, MessageSquare, Send, Download } from 'lucide-react';
import StatusBadge from '../common/StatusBadge';

const navItems = [
    { id: 'resume', label: 'Resume Optimizer', icon: FileText, path: 'resume', branchKey: 'resume_branch' },
    { id: 'interview', label: 'Interview Deck', icon: MessageSquare, path: 'interview', branchKey: 'interview_branch' },
    { id: 'outreach', label: 'Outreach Toolkit', icon: Send, path: 'outreach', branchKey: 'outreach_branch' },
    { id: 'export', label: 'Export Hub', icon: Download, path: 'export', branchKey: null } // Export has no explicit graph branch status in same way
];

export default function SidebarNavigation({ threadId }) {
    const { data: workflowMeta } = useWorkflowStatus(threadId);
    const branches = workflowMeta?.active_branches || {};

    return (
        <aside className="w-64 bg-white border-r border-gray-200 hidden md:flex flex-col">
            <nav className="flex-1 p-4 space-y-2">
                {navItems.map((item) => {
                    const Icon = item.icon;
                    const status = item.branchKey ? branches[item.branchKey] : null;
                    
                    return (
                        <NavLink 
                            key={item.id}
                            to={`/workspace/${threadId}/${item.path}`}
                            className={({ isActive }) => `
                                flex items-center justify-between p-3 rounded-lg transition-colors
                                ${isActive ? 'bg-blue-50 text-navy font-semibold' : 'text-gray-600 hover:bg-gray-50'}
                            `}
                        >
                            <div className="flex items-center gap-3">
                                <Icon className="w-5 h-5" />
                                <span className="text-sm">{item.label}</span>
                            </div>
                            {status && <StatusBadge status={status} size="small" />}
                        </NavLink>
                    );
                })}
            </nav>
        </aside>
    );
}
