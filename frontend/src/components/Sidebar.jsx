import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Building2, Filter } from 'lucide-react';

const Sidebar = () => {
  return (
    <div className="sidebar">
      <div className="sidebar-logo">
        <h2>NIFTY 100</h2>
        <p>Financial Intelligence</p>
      </div>
      
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        <NavLink 
          to="/" 
          className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}
        >
          <LayoutDashboard size={20} />
          Macro Overview
        </NavLink>
        
        <NavLink 
          to="/profile" 
          className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}
        >
          <Building2 size={20} />
          Company Profile
        </NavLink>
        
        <NavLink 
          to="/screener" 
          className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}
        >
          <Filter size={20} />
          Stock Screener
        </NavLink>
      </nav>
    </div>
  );
};

export default Sidebar;
