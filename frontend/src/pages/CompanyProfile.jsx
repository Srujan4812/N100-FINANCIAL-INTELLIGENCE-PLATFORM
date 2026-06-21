import React, { useState } from 'react';
import { getCompanyProfile } from '../services/api';
import { Search } from 'lucide-react';

const CompanyProfile = () => {
  const [ticker, setTicker] = useState('');
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!ticker) return;
    
    setLoading(true);
    setError('');
    try {
      const res = await getCompanyProfile(ticker.trim().toUpperCase());
      setProfile(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Company not found or error occurred.');
      setProfile(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>Company Profile Deep Dive</h1>
      
      <div className="glass-card" style={{ marginBottom: '2rem' }}>
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1, maxWidth: '400px' }}>
            <Search size={20} style={{ position: 'absolute', left: '12px', top: '10px', color: '#94a3b8' }} />
            <input 
              type="text" 
              placeholder="Enter NSE Ticker (e.g. TCS, RELIANCE)..."
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 10px 10px 40px',
                borderRadius: '8px',
                border: '1px solid var(--border-color)',
                background: 'rgba(0,0,0,0.2)',
                color: '#fff',
                outline: 'none',
                fontFamily: 'inherit'
              }}
            />
          </div>
          <button 
            type="submit"
            style={{
              padding: '10px 24px',
              borderRadius: '8px',
              border: 'none',
              background: 'var(--accent-blue)',
              color: '#fff',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Search
          </button>
        </form>
        {error && <p className="text-red" style={{ marginTop: '1rem' }}>{error}</p>}
      </div>

      {loading && <p>Loading profile...</p>}

      {profile && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          <div className="glass-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h2 style={{ color: 'var(--accent-blue)', fontSize: '2rem', marginBottom: '0.25rem' }}>{profile.company_name}</h2>
                <p style={{ color: 'var(--text-muted)' }}>{profile.ticker} • {profile.sector?.sub_sector || 'N/A'}</p>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--accent-green)' }}>
                  Score: {profile.latest_ratios?.composite_quality_score?.toFixed(0) || 'N/A'}/100
                </div>
              </div>
            </div>
            
            <p style={{ marginTop: '1.5rem', lineHeight: 1.6, color: '#cbd5e1' }}>
              {profile.about_company}
            </p>
          </div>

          {profile.latest_ratios && (
            <div>
              <h3>Key Performance Indicators (Latest FY)</h3>
              <div className="kpi-grid" style={{ marginTop: '1rem' }}>
                <div className="glass-card" style={{ padding: '1rem' }}>
                  <div className="kpi-label">Return on Equity</div>
                  <div className={`kpi-value ${profile.latest_ratios.return_on_equity_pct > 15 ? 'text-green' : ''}`}>
                    {profile.latest_ratios.return_on_equity_pct?.toFixed(1)}%
                  </div>
                </div>
                <div className="glass-card" style={{ padding: '1rem' }}>
                  <div className="kpi-label">Debt to Equity</div>
                  <div className={`kpi-value ${profile.latest_ratios.debt_to_equity > 1 ? 'text-red' : ''}`}>
                    {profile.latest_ratios.debt_to_equity?.toFixed(2) || '0.00'}
                  </div>
                </div>
                <div className="glass-card" style={{ padding: '1rem' }}>
                  <div className="kpi-label">Net Profit Margin</div>
                  <div className="kpi-value">{profile.latest_ratios.net_profit_margin_pct?.toFixed(1)}%</div>
                </div>
                <div className="glass-card" style={{ padding: '1rem' }}>
                  <div className="kpi-label">5Y Rev CAGR</div>
                  <div className="kpi-value">{profile.latest_ratios.revenue_cagr_5yr?.toFixed(1)}%</div>
                </div>
              </div>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
            <div className="glass-card" style={{ borderTop: '4px solid var(--accent-green)' }}>
              <h3 style={{ color: 'var(--accent-green)', marginBottom: '1rem' }}>Pros</h3>
              <ul style={{ paddingLeft: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {profile.pros?.map((pro, i) => <li key={i}>{pro}</li>)}
                {(!profile.pros || profile.pros.length === 0) && <p className="text-muted">No pros recorded.</p>}
              </ul>
            </div>
            <div className="glass-card" style={{ borderTop: '4px solid var(--accent-red)' }}>
              <h3 style={{ color: 'var(--accent-red)', marginBottom: '1rem' }}>Cons</h3>
              <ul style={{ paddingLeft: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {profile.cons?.map((con, i) => <li key={i}>{con}</li>)}
                {(!profile.cons || profile.cons.length === 0) && <p className="text-muted">No cons recorded.</p>}
              </ul>
            </div>
          </div>

        </div>
      )}
    </div>
  );
};

export default CompanyProfile;
