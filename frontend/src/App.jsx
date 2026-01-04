import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navigation from './components/Navigation';
import Dashboard from './components/Dashboard';
import SignalsPage from './components/SignalsPage';
import EntriesPage from './components/EntriesPage';
import SymbolsPage from './components/SymbolsPage';
import SettingsPage from './components/SettingsPage';
function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-100">
        <Navigation />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/signals" element={<SignalsPage />} />
          <Route path="/entries" element={<EntriesPage />} />
          <Route path="/symbols" element={<SymbolsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;