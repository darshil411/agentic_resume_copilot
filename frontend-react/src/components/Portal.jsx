import React from 'react';
import { useNavigate } from 'react-router-dom';
import { workflowService } from '../services/workflowService';
import { Upload } from 'lucide-react';

export default function Portal() {
    const navigate = useNavigate();
    const [isLoading, setIsLoading] = React.useState(false);
    const [file, setFile] = React.useState(null);
    const [jd, setJd] = React.useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!file || !jd) return;
        setIsLoading(true);
        try {
            const res = await workflowService.startWorkflow(file, jd);
            if (res && res.thread_id) {
                navigate(`/workspace/${res.thread_id}/resume`);
            }
        } catch (error) {
            console.error("Failed to start workflow:", error);
            alert("Failed to start workflow. See console.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="bg-white text-black min-h-screen flex items-center justify-center font-sans">
            <div className="max-w-xl w-full p-8">
                <div className="text-center mb-8">
                    <h1 className="text-4xl font-bold text-navy mb-2">Career Copilot</h1>
                    <p className="text-gray-500">Upload your resume and drop in a job description to get started.</p>
                </div>
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="border-dashed border-2 border-navy rounded-lg p-10 flex flex-col items-center justify-center bg-white cursor-pointer relative">
                        <Upload className="w-12 h-12 text-navy mb-3" />
                        <p className="text-navy font-medium text-center">Click or drag PDF here to upload</p>
                        <input 
                            type="file" 
                            accept=".pdf" 
                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                            onChange={(e) => setFile(e.target.files[0])}
                            required
                        />
                        {file && <p className="text-green font-semibold mt-3">Selected: {file.name}</p>}
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-navy mb-1">Job Description</label>
                        <textarea 
                            rows="4" 
                            className="w-full border border-gray-300 rounded-md shadow-sm focus:border-green focus:ring-green focus:outline-none p-3 text-black" 
                            placeholder="Paste the target job description here..."
                            value={jd}
                            onChange={(e) => setJd(e.target.value)}
                            required
                        />
                    </div>
                    <button 
                        type="submit" 
                        disabled={isLoading}
                        className="w-full py-3 bg-navy text-white hover:bg-blue-800 rounded-md font-bold text-lg flex items-center justify-center gap-2"
                    >
                        {isLoading ? 'Starting Engine...' : 'Generate Career Copilot'}
                    </button>
                </form>
            </div>
        </div>
    );
}
