import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Home from './pages/Home';
import CompanyProfile from './pages/CompanyProfile';
import Screener from './pages/Screener';

function App() {
  return (
    <Router>
      <div className="app-container">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/profile" element={<CompanyProfile />} />
            <Route path="/screener" element={<Screener />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
