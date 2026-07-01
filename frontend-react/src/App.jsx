import { BrowserRouter, Routes, Route } from 'react-router-dom';
import WorkspaceLayout from './components/WorkspaceLayout/WorkspaceLayout';
import ResumeWorkspace from './components/ResumeWorkspace/ResumeWorkspace';
import InterviewWorkspace from './components/InterviewWorkspace/InterviewWorkspace';
import OutreachWorkspace from './components/OutreachWorkspace/OutreachWorkspace';
import ExportWorkspace from './components/ExportWorkspace/ExportWorkspace';
// We need a placeholder Portal component
import Portal from './components/Portal';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Portal />} />
        <Route path="/workspace/:threadId" element={<WorkspaceLayout />}>
          <Route path="resume" element={<ResumeWorkspace />} />
          <Route path="interview" element={<InterviewWorkspace />} />
          <Route path="outreach" element={<OutreachWorkspace />} />
          <Route path="export" element={<ExportWorkspace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
