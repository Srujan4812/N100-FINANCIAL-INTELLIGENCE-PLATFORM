import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_URL,
});

export const getHealth = () => api.get('/health');
export const getCompanies = (sector) => api.get('/companies', { params: { sector } });
export const getCompanyProfile = (ticker) => api.get(`/companies/${ticker}`);
export const getCompanyPl = (ticker) => api.get(`/companies/${ticker}/pl`);
export const getScreenerResults = (params) => api.get('/screener', { params });
export const getSectorsSummary = () => api.get('/sectors');
export const getPortfolioStats = () => api.get('/portfolio/stats');
