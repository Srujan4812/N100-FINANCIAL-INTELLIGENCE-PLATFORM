import React, { useState, useEffect } from 'react';
import { getScreenerResults } from '../services/api';

const Screener = () => {
  const [minRoe, setMinRoe] = useState(15);
  const [maxDe, setMaxDe] = useState(1.0);
  const [minCagr, setMinCagr] = useState(10);
  
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchResults = async () => {
    setLoading(true);
    try {
      const res = await getScreenerResults({ min_roe: minRoe, max_de: maxDe, min_cagr: minCagr });
      setResults(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
    // eslint-disable-next-line
  }, [minRoe, maxDe, minCagr]);

  return (
    <div>
      <h1>Multi-Criteria Investment Screener</h1>
      
      <div className="glass-card" style={{ marginBottom: '2rem', display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: '200px' }}>
          <label style={{ display: 'block', color: 'var(--text-muted)', marginBottom: '0.5rem', fontWeight: 600 }}>
            Minimum ROE (%)
          </label>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <input 
              type="range" 
              min="-20" max="50" 
              value={minRoe} 
              onChange={(e) => setMinRoe(Number(e.target.value))}
              style={{ flex: 1 }}
            />
            <span style={{ fontWeight: 700, width: '40px', textAlign: 'right' }}>{minRoe}%</span>
          </div>
        </div>

        <div style={{ flex: 1, minWidth: '200px' }}>
          <label style={{ display: 'block', color: 'var(--text-muted)', marginBottom: '0.5rem', fontWeight: 600 }}>
            Maximum Debt/Equity
          </label>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <input 
              type="range" 
              min="0" max="5" step="0.1"
              value={maxDe} 
              onChange={(e) => setMaxDe(Number(e.target.value))}
              style={{ flex: 1 }}
            />
            <span style={{ fontWeight: 700, width: '40px', textAlign: 'right' }}>{maxDe}</span>
          </div>
        </div>

        <div style={{ flex: 1, minWidth: '200px' }}>
          <label style={{ display: 'block', color: 'var(--text-muted)', marginBottom: '0.5rem', fontWeight: 600 }}>
            Minimum 5Y Rev CAGR (%)
          </label>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <input 
              type="range" 
              min="-20" max="40" 
              value={minCagr} 
              onChange={(e) => setMinCagr(Number(e.target.value))}
              style={{ flex: 1 }}
            />
            <span style={{ fontWeight: 700, width: '40px', textAlign: 'right' }}>{minCagr}%</span>
          </div>
        </div>
      </div>

      <div className="glass-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2>Screener Results</h2>
          <div className="text-muted">{results.length} companies matched</div>
        </div>
        
        {loading ? (
          <p>Running screen...</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Ticker</th>
                  <th>Company Name</th>
                  <th>Sector</th>
                  <th>Score</th>
                  <th>ROE</th>
                  <th>D/E</th>
                  <th>5Y Rev CAGR</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, index) => (
                  <tr key={r.company_id}>
                    <td>#{index + 1}</td>
                    <td style={{ fontWeight: 700, color: 'var(--accent-blue)' }}>{r.company_id}</td>
                    <td>{r.company_name}</td>
                    <td>{r.broad_sector}</td>
                    <td style={{ fontWeight: 600, color: 'var(--accent-green)' }}>
                      {r.composite_quality_score?.toFixed(0) || '-'}
                    </td>
                    <td>{r.return_on_equity_pct?.toFixed(1) || '-'}%</td>
                    <td>{r.debt_to_equity?.toFixed(2) || '-'}</td>
                    <td>{r.revenue_cagr_5yr?.toFixed(1) || '-'}%</td>
                  </tr>
                ))}
                {results.length === 0 && (
                  <tr>
                    <td colSpan="8" style={{ textAlign: 'center', padding: '2rem' }}>No companies matched the criteria.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default Screener;
