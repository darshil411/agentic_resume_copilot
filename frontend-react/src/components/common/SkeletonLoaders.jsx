import React from 'react';

export function CardSkeleton() {
    return (
        <div className="bg-white p-5 rounded-lg border border-gray-200 w-full h-48 flex flex-col">
            <div className="skeleton-shimmer h-4 w-1/3 mb-4 rounded"></div>
            <div className="skeleton-shimmer h-3 w-full mb-2 rounded"></div>
            <div className="skeleton-shimmer h-3 w-5/6 mb-2 rounded"></div>
            <div className="skeleton-shimmer h-3 w-4/5 rounded mt-auto"></div>
        </div>
    );
}

export function ResumePaneSkeleton() {
    return (
        <div className="p-6 w-full">
            <div className="skeleton-shimmer h-6 w-1/3 mb-6 rounded"></div>
            <div className="skeleton-shimmer h-4 w-full mb-2 rounded"></div>
            <div className="skeleton-shimmer h-4 w-11/12 mb-2 rounded"></div>
            <div className="skeleton-shimmer h-4 w-5/6 mb-6 rounded"></div>
            
            <div className="skeleton-shimmer h-5 w-1/4 mb-4 rounded"></div>
            <div className="skeleton-shimmer h-4 w-full mb-2 rounded"></div>
            <div className="skeleton-shimmer h-4 w-4/5 mb-2 rounded"></div>
        </div>
    );
}
