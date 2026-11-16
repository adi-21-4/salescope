import { useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  BarChart3,
  CircleHelp,
  Database,
  Lightbulb,
  LogOut,
  Menu,
  MessageSquareText,
  Store,
  Upload,
  X,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  function closeMobileNav() {
    setMobileNavOpen(false);
  }

  const shopName = user?.shop_name || "Your store";
  const avatar = shopName.trim().slice(0, 1).toUpperCase();
  const dashboardPath = pathname.match(/^\/dashboard\/[^/]+/)?.[0] ?? "/dashboard";

  return (
    <div className={`app-shell${mobileNavOpen ? " app-shell--nav-open" : ""}`}>
      <a className="skip-to-content" href="#workspace-main">Skip to content</a>
      <aside className="app-sidebar" aria-label="SalesScope navigation">
        <Link className="app-brand" to="/dashboard" onClick={closeMobileNav} aria-label="SalesScope dashboard">
          <span className="app-brand-mark" aria-hidden="true"><BarChart3 size={19} strokeWidth={2.4} /></span>
          <span className="app-brand-name">salescope<span>.</span><small>Retail analytics</small></span>
        </Link>

        <div className="sidebar-workspace">
          <span className="store-avatar"><Store size={16} /></span>
          <span className="store-label"><strong>{shopName}</strong><small>Workspace</small></span>
        </div>

        <nav className="app-nav">
          <p className="app-nav-label">Workspace</p>
          <NavLink to="/dashboard" className={({ isActive }) => `app-nav-link${isActive ? " is-active" : ""}`} onClick={closeMobileNav}>
            <BarChart3 size={17} strokeWidth={1.9} /><span>Overview</span>
          </NavLink>
          <NavLink to="/upload" className={({ isActive }) => `app-nav-link${isActive ? " is-active" : ""}`} onClick={closeMobileNav}>
            <Upload size={17} strokeWidth={1.9} /><span>Import sales</span>
          </NavLink>
          <a className="app-nav-link" href={`${dashboardPath}#insights`} onClick={closeMobileNav}>
            <Lightbulb size={17} strokeWidth={1.9} /><span>AI insights</span>
          </a>
          <a className="app-nav-link" href={`${dashboardPath}#ask-your-data`} onClick={closeMobileNav}>
            <MessageSquareText size={17} strokeWidth={1.9} /><span>Ask your data</span>
          </a>
        </nav>

        <div className="sidebar-bottom">
          <div className="privacy-note"><span className="privacy-icon"><Database size={15} /></span><span><strong>Your data, in focus</strong><small>Private to your workspace</small></span></div>
          <button className="sidebar-logout" type="button" onClick={handleLogout}><LogOut size={16} /><span>Log out</span></button>
          <a className="sidebar-help" href="mailto:support@salesscope.example"><CircleHelp size={15} /> Help &amp; support</a>
        </div>
      </aside>

      <button className="mobile-scrim" type="button" aria-label="Close navigation" onClick={closeMobileNav} tabIndex={mobileNavOpen ? 0 : -1} />

      <div className="app-workspace">
        <header className="app-topbar">
          <button className="mobile-nav-toggle" type="button" aria-label={mobileNavOpen ? "Close navigation" : "Open navigation"} aria-expanded={mobileNavOpen} onClick={() => setMobileNavOpen((open) => !open)}>
            {mobileNavOpen ? <X size={19} /> : <Menu size={19} />}
          </button>
          <div className="topbar-context"><span>Workspace</span><span className="context-separator">/</span><strong>{shopName}</strong></div>
          <div className="topbar-account"><span className="account-status"><i /> Data ready</span><span className="account-avatar" aria-hidden="true">{avatar}</span></div>
        </header>
        <main className="app-main" id="workspace-main"><Outlet /></main>
      </div>
    </div>
  );
}
