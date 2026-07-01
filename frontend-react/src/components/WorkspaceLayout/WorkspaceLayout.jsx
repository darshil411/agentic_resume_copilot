import React from 'react';
import { Outlet, useParams } from 'react-router-dom';
import Header from './Header';
import SidebarNavigation from './SidebarNavigation';
import ErrorBoundary from '../common/ErrorBoundary';

export default function WorkspaceLayout() {
    const { threadId } = useParams();

    return (
        <div className="bg-gray-50 text-black min-h-screen font-sans flex flex-col">
            <Header />
            <div className="flex flex-1 overflow-hidden">
                <SidebarNavigation threadId={threadId} />
                <main className="flex-1 overflow-y-auto p-4 md:p-8">
                    <ErrorBoundary>
                        <Outlet />
                    </ErrorBoundary>
                </main>
            </div>
        </div>
    );
}
