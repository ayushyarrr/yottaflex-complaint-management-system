
import { useEffect, useState } from 'react'
import Complaints from './Complaints'
import SLAMonitoring from './SLAMonitoring'
import Analytics from './Analytics'
import './App.css'

const API_URL = 'http://127.0.0.1:8000'

interface AnalyticsData {
  overview: {
    total_complaints: number
    open_complaints: number
    reopened_complaints: number
    average_resolution_hours: number
  }
  status_distribution: Record<string, number>
  priority_distribution: Record<string, number>
  category_distribution: Record<string, number>
  sla: {
    total_sla_cycles: number
    response_breaches: number
    response_breach_rate_percent: number
    resolution_breaches: number
    resolution_breach_rate_percent: number
    rate_denominator: string
  }
  customer_satisfaction: {
    survey_count: number
    average_rating: number
    rating_distribution: Record<string, number>
  }
}

const priorityColors: Record<string, string> = {
  P1: '#dc4444',
  P2: '#e58a36',
  P3: '#d3a62e',
  P4: '#279b73',
}

const statusLabels: Record<string, string> = {
  NEW: 'New',
  CLASSIFIED: 'Classified',
  ASSIGNED: 'Assigned',
  IN_PROGRESS: 'In progress',
  PENDING_CUSTOMER: 'Pending customer',
  RESOLVED: 'Resolved',
  CLOSED: 'Closed',
}

function App() {
  const [activePage, setActivePage] = useState<
  'dashboard' | 'complaints' | 'sla' | 'analytics'
>('dashboard') 
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [lastUpdated, setLastUpdated] = useState('')

  async function loadAnalytics() {
    try {
      setLoading(true)
      setError('')

      const response = await fetch(`${API_URL}/api/analytics`)

      if (!response.ok) {
        throw new Error(`API returned status ${response.status}`)
      }

      const data: AnalyticsData = await response.json()
      setAnalytics(data)
      setLastUpdated(new Date().toLocaleTimeString())
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to connect to the backend.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAnalytics()
  }, [])

  const totalForPriorities = analytics
    ? Object.values(analytics.priority_distribution).reduce(
        (sum, value) => sum + value,
        0,
      )
    : 0

  const totalForStatuses = analytics
    ? Object.values(analytics.status_distribution).reduce(
        (sum, value) => sum + value,
        0,
      )
    : 0

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">Y</div>
          <div>
            <h2>YottaFlex</h2>
            <span>COMPLAINT OPERATIONS</span>
          </div>
        </div>

        <div className="sidebar-section-label">WORKSPACE</div>

        <nav className="navigation">
          <button
            className={`nav-item ${activePage === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActivePage('dashboard')}
          >
            <span className="nav-icon">▦</span>
            Dashboard
          </button>

          <button
            className={`nav-item ${activePage === 'complaints' ? 'active' : ''}`}
            onClick={() => setActivePage('complaints')}
          >
            <span className="nav-icon">▤</span>
            Complaints
          </button>

          <button
            className={`nav-item ${activePage === 'sla' ? 'active' : ''}`}
            onClick={() => setActivePage('sla')}
          >
            <span className="nav-icon">◷</span>
            SLA Monitoring
          </button>

          <button
            className={`nav-item ${activePage === 'analytics' ? 'active' : ''}`}
            onClick={() => setActivePage('analytics')}
          >
            <span className="nav-icon">▥</span>
            Analytics
          </button>
        </nav>

        <div className="sidebar-bottom">
          <div className="system-status">
            <span className="status-dot" />
            <div>
              <strong>System operational</strong>
              <small>Backend connection</small>
            </div>
          </div>
          <div className="sidebar-footer">YottaFlex AI · 2026</div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <div className="breadcrumb">Workspace / Dashboard</div>
            <h1>Overview</h1>
          </div>

          <div className="topbar-actions">
            <span className="live-indicator">
              <span className="status-dot" />
              Live data
            </span>
            <button
              className="refresh-button"
              onClick={loadAnalytics}
              disabled={loading}
            >
              ↻ <span>Refresh</span>
            </button>
            <div className="avatar">A</div>
          </div>
        </header>

{activePage === 'complaints' ? (
  <Complaints />
) : activePage === 'sla' ? (
  <SLAMonitoring />
) : activePage === 'analytics' ? (
  <Analytics
    analytics={analytics}
    loading={loading}
    error={error}
    lastUpdated={lastUpdated}
    onRefresh={loadAnalytics}
  />
) : (
  <>

        <section className="page-intro">
          <div>
            <h2>Complaint operations</h2>
            <p>
              Monitor customer complaints, priorities, resolution performance
              and service-level agreements.
            </p>
          </div>
          <span className="date-label">DATA FROM LOCAL DATABASE</span>
        </section>

        {error && (
          <div className="error-banner">
            <strong>Unable to load analytics.</strong>
            <span>{error}</span>
            <button onClick={loadAnalytics}>Try again</button>
          </div>
        )}

        {loading && !analytics ? (
          <div className="loading-panel">Loading dashboard data...</div>
        ) : analytics ? (
          <>
            <section className="metric-grid">
              <MetricCard
                label="Total complaints"
                value={analytics.overview.total_complaints}
                icon="▤"
                detail="All recorded complaints"
                accent="blue"
              />
              <MetricCard
                label="Open complaints"
                value={analytics.overview.open_complaints}
                icon="◷"
                detail="Awaiting completion"
                accent="orange"
              />
              <MetricCard
                label="Reopened complaints"
                value={analytics.overview.reopened_complaints}
                icon="↻"
                detail="Distinct reopened cases"
                accent="purple"
              />
              <MetricCard
                label="Avg. resolution time"
                value={`${analytics.overview.average_resolution_hours}h`}
                icon="◴"
                detail="Final resolutions only"
                accent="green"
              />
            </section>

            <section className="dashboard-grid">
              <div className="panel priority-panel">
                <div className="panel-heading">
                  <div>
                    <h3>Priority distribution</h3>
                    <p>Complaints grouped by urgency</p>
                  </div>
                  <span className="panel-tag">PRIORITY</span>
                </div>

                <div className="priority-list">
                  {Object.entries(analytics.priority_distribution).map(
                    ([priority, count]) => (
                      <div className="distribution-row" key={priority}>
                        <div className="distribution-label">
                          <span
                            className="priority-indicator"
                            style={{
                              backgroundColor: priorityColors[priority],
                            }}
                          />
                          <strong>{priority}</strong>
                          <span className="distribution-count">{count}</span>
                        </div>
                        <div className="progress-track">
                          <div
                            className="progress-fill"
                            style={{
                              width: `${
                                totalForPriorities
                                  ? (count / totalForPriorities) * 100
                                  : 0
                              }%`,
                              backgroundColor: priorityColors[priority],
                            }}
                          />
                        </div>
                      </div>
                    ),
                  )}
                </div>
                <div className="panel-footnote">
                  {totalForPriorities} complaints classified by priority
                </div>
              </div>

              <div className="panel sla-panel">
                <div className="panel-heading">
                  <div>
                    <h3>SLA performance</h3>
                    <p>Recorded service-level breaches</p>
                  </div>
                  <span className="panel-tag">SLA</span>
                </div>

                <div className="sla-metric">
                  <div>
                    <span>Response breach rate</span>
                    <strong>
                      {analytics.sla.response_breach_rate_percent}%
                    </strong>
                  </div>
                  <div className="sla-track">
                    <div
                      className="sla-fill response-fill"
                      style={{
                        width: `${Math.min(
                          analytics.sla.response_breach_rate_percent,
                          100,
                        )}%`,
                      }}
                    />
                  </div>
                  <small>
                    {analytics.sla.response_breaches} recorded breaches
                  </small>
                </div>

                <div className="sla-metric">
                  <div>
                    <span>Resolution breach rate</span>
                    <strong>
                      {analytics.sla.resolution_breach_rate_percent}%
                    </strong>
                  </div>
                  <div className="sla-track">
                    <div
                      className="sla-fill resolution-fill"
                      style={{
                        width: `${Math.min(
                          analytics.sla.resolution_breach_rate_percent,
                          100,
                        )}%`,
                      }}
                    />
                  </div>
                  <small>
                    {analytics.sla.resolution_breaches} recorded breaches
                  </small>
                </div>

                <div className="panel-footnote">
                  Based on {analytics.sla.total_sla_cycles} SLA cycles
                </div>
              </div>
            </section>

            <section className="dashboard-grid lower-grid">
              <div className="panel status-panel">
                <div className="panel-heading">
                  <div>
                    <h3>Complaint status</h3>
                    <p>Current workflow distribution</p>
                  </div>
                  <span className="panel-tag">LIFECYCLE</span>
                </div>

                <div className="status-list">
                  {Object.entries(analytics.status_distribution).map(
                    ([status, count]) => (
                      <div className="status-row" key={status}>
                        <span>{statusLabels[status] || status}</span>
                        <div className="status-count-area">
                          <div className="mini-track">
                            <div
                              className="mini-fill"
                              style={{
                                width: `${
                                  totalForStatuses
                                    ? (count / totalForStatuses) * 100
                                    : 0
                                }%`,
                              }}
                            />
                          </div>
                          <strong>{count}</strong>
                        </div>
                      </div>
                    ),
                  )}
                </div>
              </div>

              <div className="panel category-panel">
                <div className="panel-heading">
                  <div>
                    <h3>Complaint categories</h3>
                    <p>Distribution across issue types</p>
                  </div>
                  <span className="panel-tag">CATEGORIES</span>
                </div>

                <div className="category-list">
                  {Object.entries(analytics.category_distribution)
                    .sort((a, b) => b[1] - a[1])
                    .map(([category, count]) => (
                      <div className="category-row" key={category}>
                        <span>{category}</span>
                        <strong>{count}</strong>
                      </div>
                    ))}
                </div>
              </div>
            </section>

            <section className="panel satisfaction-panel">
              <div className="panel-heading">
                <div>
                  <h3>Customer satisfaction</h3>
                  <p>Ratings submitted after complaint closure</p>
                </div>
                <span className="panel-tag">CUSTOMER FEEDBACK</span>
              </div>

              <div className="satisfaction-content">
                <div className="rating-summary">
                  <strong>
                    {analytics.customer_satisfaction.average_rating.toFixed(2)}
                  </strong>
                  <span className="rating-stars">★★★★★</span>
                  <small>
                    Average rating from{' '}
                    {analytics.customer_satisfaction.survey_count} surveys
                  </small>
                </div>

                <div className="rating-distribution">
                  {Object.entries(
                    analytics.customer_satisfaction.rating_distribution,
                  )
                    .reverse()
                    .map(([rating, count]) => (
                      <div className="rating-row" key={rating}>
                        <span>{rating} ★</span>
                        <div className="rating-track">
                          <div
                            className="rating-fill"
                            style={{
                              width: `${
                                analytics.customer_satisfaction.survey_count
                                  ? (count /
                                      analytics.customer_satisfaction
                                        .survey_count) *
                                    100
                                  : 0
                              }%`,
                            }}
                          />
                        </div>
                        <strong>{count}</strong>
                      </div>
                    ))}
                </div>
              </div>
            </section>

            <footer className="dashboard-footer">
              <span>
                YottaFlex Complaint Management System · Operational Dashboard
              </span>
              <span>Last updated: {lastUpdated}</span>
            </footer>
          </>
        ) : (
          <div className="loading-panel">
            No analytics data is available.
          </div>
        )}
  </>
)}
      </main>
    </div>
  )
}

interface MetricCardProps {
  label: string
  value: string | number
  icon: string
  detail: string
  accent: string
}

function MetricCard({
  label,
  value,
  icon,
  detail,
  accent,
}: MetricCardProps) {
  return (
    <div className="metric-card">
      <div className="metric-top">
        <span>{label}</span>
        <div className={`metric-icon ${accent}`}>{icon}</div>
      </div>
      <strong className="metric-value">{value}</strong>
      <small>{detail}</small>
    </div>
  )
}

export default App
