import React from 'react';
import { WorkflowStatus } from '../../models/enums';

export default function StatusBadge({ status, size = 'default' }) {
    let colorClass = 'bg-gray-100 text-gray-600';
    let label = status;
    let pulse = false;

    switch (status) {
        case WorkflowStatus.PROCESSING:
            colorClass = 'bg-blue-100 text-blue-700';
            label = 'Processing';
            break;
        case WorkflowStatus.ACTION_REQUIRED:
        case WorkflowStatus.WAITING:
            colorClass = 'bg-yellow-100 text-yellow-700';
            label = 'Action Required';
            pulse = true;
            break;
        case WorkflowStatus.READY:
        case WorkflowStatus.COMPLETED:
            colorClass = 'bg-green-100 text-green-700';
            label = 'Ready';
            break;
        case WorkflowStatus.FAILED:
            colorClass = 'bg-red-100 text-red-700';
            label = 'Failed';
            break;
    }

    const padding = size === 'small' ? 'px-2 py-0.5 text-[10px]' : 'px-3 py-1 text-xs';

    return (
        <span className={`rounded-full font-semibold uppercase tracking-wider ${padding} ${colorClass} ${pulse ? 'animate-pulse' : ''}`}>
            {label}
        </span>
    );
}
