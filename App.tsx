
import React from 'react';
import { HashRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Home } from './components/Home';
import { GovLens } from './components/GovLens';
import { LexGraph } from './components/LexGraph';
import { ForesightOps } from './components/ForesightOps/index';
import { AccessBridge } from './components/AccessBridge/index';
import { GovernanceDashboard } from './components/GovernanceDashboard';
import { KnowledgeBase } from './components/KnowledgeBase/index';
import { DocumentViewer } from './components/DocumentViewer';
import { LanguageProvider } from './contexts/LanguageContext';
import { AccessibilityProvider } from './contexts/AccessibilityContext';
import { ApiKeyProvider } from './contexts/ApiKeyContext';
import { ErrorBoundary } from './components/ui/ErrorBoundary';

function App() {
  return (
    <AccessibilityProvider>
    <LanguageProvider>
    <ApiKeyProvider>
      <HashRouter>
        <ErrorBoundary>
          <Layout>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/knowledge-base" element={<KnowledgeBase />} />
              <Route path="/insights" element={<GovLens />} />
              <Route path="/rules" element={<LexGraph />} />
              <Route path="/plan" element={<ForesightOps />} />
              <Route path="/assist" element={<AccessBridge />} />
              <Route path="/governance" element={<GovernanceDashboard />} />
              <Route path="/documents/:docId" element={<DocumentViewer />} />
            </Routes>
          </Layout>
        </ErrorBoundary>
      </HashRouter>
    </ApiKeyProvider>
    </LanguageProvider>
    </AccessibilityProvider>
  );
}

export default App;
