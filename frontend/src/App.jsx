import React from 'react'
import { BrowserRouter, Routes, Route, NavLink, Link } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { CloudSun, Database, Github, LayoutDashboard } from 'lucide-react'
import Home from './pages/Home'
import History from './pages/History'
import QueryDetail from './pages/QueryDetail'
import './index.css'

function Navbar() {
  const linkCls = ({ isActive }) =>
    `flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
      isActive
        ? 'bg-primary/10 text-primary'
        : 'text-slate-500 hover:text-primary hover:bg-primary/5'
    }`

  return (
    <nav className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-sm">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5 font-bold text-xl text-text-main">
          <CloudSun className="w-6 h-6 text-primary" />
          Weather<span className="text-primary">Vault</span>
        </Link>

        {/* Nav links */}
        <div className="flex items-center gap-1">
          <NavLink to="/" end className={linkCls}>
            <LayoutDashboard className="w-4 h-4" />
            <span className="hidden sm:inline">Live Weather</span>
          </NavLink>
          <NavLink to="/history" className={linkCls}>
            <Database className="w-4 h-4" />
            <span className="hidden sm:inline">History</span>
          </NavLink>
          <a
            href="http://localhost:8000/api/v1/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-slate-500 hover:text-primary hover:bg-primary/5 transition-colors"
          >
            <Github className="w-4 h-4" />
            <span className="hidden sm:inline">API Docs</span>
          </a>
        </div>
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#FFFFFF',
            color: '#0F172A',
            border: '1px solid #E2E8F0',
            borderRadius: '12px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
          },
        }}
      />
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/history" element={<History />} />
          <Route path="/query/:id" element={<QueryDetail />} />
        </Routes>
      </main>
      <footer className="border-t border-slate-200 mt-16 py-6 text-center text-slate-400 text-sm">
        WeatherVault © {new Date().getFullYear()} — Built with FastAPI, PostgreSQL & React
      </footer>
    </BrowserRouter>
  )
}
