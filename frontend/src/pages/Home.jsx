import React, { useEffect, useState } from 'react';
import { getSectorsSummary } from '../services/api';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

const Home = () => {
  const [sectors, setSectors] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSectors = async () => {
      try {
        const response = await getSectorsSummary();
        setSectors(response.data);
      } catch (error) {
        console.error('Error fetching sectors:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchSectors();
  }, []);

  const totalCompanies = sectors.reduce((acc, curr) => acc + curr.company_count, 0);
  const avgRoe = sectors.reduce((acc, curr) => acc + (curr.median_roe || 0), 0) / (sectors.length || 1);

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#6366f1', '#84cc16'];

  if (loading) return <div className="p-4">Loading Macro Overview...</div>;

  return (
    <div>
      <h1>Nifty 100 Financial Intelligence Platform</h1>
      
      <div className="banner">
        <h2>System Overview</h2>
        <p>Welcome to the Nifty 100 fundamental research workspace. This modern web interface aggregates 14 years of P&L, Balance Sheet, and Cash Flow filings for Nifty 100 constituents.</p>
      </div>

      <div className="kpi-grid">
        <div className="glass-card">
          <div className="kpi-label">Universe Size</div>
          <div className="kpi-value">{totalCompanies}</div>
          <div className="kpi-label text-green">Active Constituents</div>
        </div>
        <div className="glass-card">
          <div className="kpi-label">Avg Sector ROE</div>
          <div className="kpi-value">{avgRoe.toFixed(1)}%</div>
          <div className="kpi-label text-green">Profitability Metric</div>
        </div>
        <div className="glass-card">
          <div className="kpi-label">Sectors Covered</div>
          <div className="kpi-value">{sectors.length}</div>
          <div className="kpi-label text-green">Macro Diversification</div>
        </div>
      </div>

      <div className="glass-card" style={{ marginTop: '2rem' }}>
        <h2>Industry & Sector Allocation</h2>
        <div style={{ display: 'flex', gap: '2rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ height: 350, flex: 1, minWidth: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={sectors}
                  dataKey="company_count"
                  nameKey="sector"
                  cx="50%"
                  cy="50%"
                  innerRadius={80}
                  outerRadius={120}
                  paddingAngle={2}
                >
                  {sectors.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                  itemStyle={{ color: '#fff' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          
          <div style={{ flex: 1, minWidth: '300px', overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Sector</th>
                  <th>Companies</th>
                  <th>Median ROE</th>
                  <th>Median D/E</th>
                </tr>
              </thead>
              <tbody>
                {sectors.map((s) => (
                  <tr key={s.sector}>
                    <td style={{ fontWeight: 500 }}>{s.sector}</td>
                    <td>{s.company_count}</td>
                    <td className={s.median_roe > 15 ? 'text-green' : ''}>
                      {s.median_roe ? s.median_roe.toFixed(1) + '%' : '-'}
                    </td>
                    <td className={s.median_de > 1 ? 'text-red' : ''}>
                      {s.median_de ? s.median_de.toFixed(2) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;
