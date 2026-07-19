import React from 'react';
import { useNavigate } from 'react-router-dom';
import { workflowService } from '../services/workflowService';
import { Upload, Check, X } from 'lucide-react';

export default function Portal() {
    const navigate = useNavigate();
    const [isLoading, setIsLoading] = React.useState(false);
    const [file, setFile] = React.useState(null);
    const [jd, setJd] = React.useState('');
    const [projectDocs, setProjectDocs] = React.useState([]);
    const [docError, setDocError] = React.useState('');

    const handleDocUpload = (e) => {
        const files = Array.from(e.target.files);
        setDocError('');
        
        if (projectDocs.length + files.length > 5) {
            setDocError('Maximum 5 files allowed.');
            return;
        }

        const validExtensions = ['.md', '.txt', '.pdf'];
        const validTypes = ['text/markdown', 'text/plain', 'application/pdf'];
        
        const validFiles = files.filter(f => {
            const ext = f.name.substring(f.name.lastIndexOf('.')).toLowerCase();
            return validTypes.includes(f.type) || validExtensions.includes(ext) || f.name.endsWith('.md');
        });

        if (validFiles.length !== files.length) {
            setDocError('Only .md, .txt, and .pdf files are supported.');
        }

        setProjectDocs(prev => [...prev, ...validFiles].slice(0, 5));
        // Reset input value so the same file can be selected again if removed
        e.target.value = null;
    };

    const removeDoc = (index) => {
        setProjectDocs(prev => prev.filter((_, i) => i !== index));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!file || !jd) return;
        setIsLoading(true);
        try {
            const res = await workflowService.startWorkflow(file, jd, projectDocs);
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

                    <div className="relative py-4">
                        <div className="absolute inset-0 flex items-center" aria-hidden="true">
                            <div className="w-full border-t border-gray-300"></div>
                        </div>
                        <div className="relative flex justify-center">
                            <span className="bg-white px-3 text-sm font-semibold text-gray-500 uppercase tracking-wider">
                                Optional AI Enhancement
                            </span>
                        </div>
                    </div>

                    <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
                        <div className="flex items-center gap-2 mb-2">
                            <span className="text-xl">🧠</span>
                            <h3 className="text-lg font-bold text-navy">Project Knowledge Base</h3>
                        </div>
                        <p className="text-gray-600 text-sm mb-4">
                            Upload README files or technical documentation.
                        </p>
                        
                        <div className="text-sm text-gray-700 mb-4 space-y-1">
                            <p className="font-semibold text-navy">The AI will:</p>
                            <p className="flex items-center gap-2"><Check className="w-4 h-4 text-green" /> Select the most relevant projects</p>
                            <p className="flex items-center gap-2"><Check className="w-4 h-4 text-green" /> Extract technical implementation details</p>
                            <p className="flex items-center gap-2"><Check className="w-4 h-4 text-green" /> Improve ATS keyword coverage</p>
                            <p className="flex items-center gap-2"><Check className="w-4 h-4 text-green" /> Strengthen project descriptions</p>
                        </div>

                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
                            <div className="text-xs text-gray-500">
                                Supported:<br/>.md, .txt, .pdf (Max 5)
                            </div>
                            <div className="relative">
                                <input
                                    type="file"
                                    multiple
                                    accept=".md,.txt,.pdf,text/markdown,text/plain,application/pdf"
                                    onChange={handleDocUpload}
                                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                    disabled={projectDocs.length >= 5}
                                />
                                <button
                                    type="button"
                                    className="bg-white border border-gray-300 text-navy px-4 py-2 rounded-md font-medium text-sm hover:bg-gray-50 flex items-center gap-2 w-full sm:w-auto justify-center disabled:opacity-50"
                                    disabled={projectDocs.length >= 5}
                                >
                                    + Add Project Documents
                                </button>
                            </div>
                        </div>

                        {docError && <p className="text-red-500 text-sm mb-3">{docError}</p>}

                        {projectDocs.length > 0 && (
                            <div className="mt-4 border-t border-gray-200 pt-4">
                                <p className="text-sm font-semibold text-navy mb-2">
                                    Selected Files ({projectDocs.length}/5)
                                </p>
                                <ul className="space-y-2">
                                    {projectDocs.map((doc, index) => (
                                        <li key={index} className="flex items-center justify-between text-sm bg-white p-2 border border-gray-200 rounded">
                                            <div className="flex items-center gap-2 truncate">
                                                <Check className="w-4 h-4 text-green shrink-0" />
                                                <span className="truncate" title={doc.name}>{doc.name}</span>
                                            </div>
                                            <button
                                                type="button"
                                                onClick={() => removeDoc(index)}
                                                className="text-gray-400 hover:text-red-500 p-1"
                                                title="Remove file"
                                            >
                                                <X className="w-4 h-4" />
                                            </button>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
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
