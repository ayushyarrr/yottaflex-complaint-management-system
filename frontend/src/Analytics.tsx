
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

interface AnalyticsProps {
  analytics: AnalyticsData | null
  loading: boolean
  error: string
  lastUpdated: string
  onRefresh: () => void
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

function Analytics({
  analytics,
  loading,
  error,
  lastUpdated,
  onRefresh,
}: AnalyticsProps) {
  if (loading && !analytics) {
    return <div className="loading-panel">Loading analytics...</div>
  }

  if (error && !analytics) {
    return (
      <div className="error-banner">
        <strong>Unable to load analytics.</strong>
        <span>{error}</span>
        <button onClick={onRefresh}>Try again</button>
      </div>
    )
  }

  if (!analytics) {
    return <div className="loading-panel">No analytics data available.</div>
  }

  const priorityTotal = Object.values(
    analytics.priority_distribution,
  ).reduce((sum, value) => sum + value, 0)

  const statusTotal = Object.values(
    analytics.status_distribution,
  ).reduce((sum, value) => sum + value, 0)

  const surveyTotal = analytics.customer_satisfaction.survey_count

  return (
    <>
      <section className="page-intro">
        <div>
          <h2>Operational analytics</h2>
          <p>
            Detailed insights into complaint trends, service performance,
            workflow distribution and customer satisfaction.
          </p>
        </div>
        <span className="date-label">LIVE DATABASE METRICS</span>
      </section>

      {error && (
        <div className="error-banner">
          <strong>Refresh warning</strong>
          <span>{error}</span>
        </div>
      )}

      <section className="metric-grid">
        <div className="metric-card">
          <div className="metric-top">
            <span>Total SLA cycles</span>
            <div className="metric-icon blue">◷</div>
          </div>
          <strong className="metric-value">
            {analytics.sla.total_sla_cycles}
          </strong>
          <small>Includes reopened complaint cycles</small>
        </div>

        <div className="metric-card">
          <div className="metric-top">
            <span>Response breaches</span>
            <div className="metric-icon orange">!</div>
          </div>
          <strong className="metric-value">
            {analytics.sla.response_breaches}
          </strong>
          <small>
            {analytics.sla.response_breach_rate_percent}% of SLA cycles
          </small>
        </div>

        <div className="metric-card">
          <div className="metric-top">
            <span>Resolution breaches</span>
            <div className="metric-icon purple">!</div>
          </div>
          <strong className="metric-value">
            {analytics.sla.resolution_breaches}
          </strong>
          <small>
            {analytics.sla.resolution_breach_rate_percent}% of SLA cycles
          </small>
        </div>

        <div className="metric-card">
          <div className="metric-top">
            <span>Customer rating</span>
            <div className="metric-icon green">★</div>
          </div>
          <strong className="metric-value">
            {analytics.customer_satisfaction.average_rating.toFixed(2)}/5
          </strong>
          <small>Based on {surveyTotal} submitted surveys</small>
        </div>
      </section>

      <section className="dashboard-grid">
        <div className="panel priority-panel">
          <div className="panel-heading">
            <div>
              <h3>Priority distribution</h3>
              <p>Complaint volume by urgency level</p>
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
                        backgroundColor:
                          priorityColors[priority] || '#64748b',
                      }}
                    />
                    <strong>{priority}</strong>
                    <span className="distribution-count">{count}</span>
                  </div>
                  <div className="progress-track">
                    <div
                      className="progress-fill"
                      style={{
                        width: `${priorityTotal
                          ? (count / priorityTotal) * 100
                          : 0}%`,
                        backgroundColor:
                          priorityColors[priority] || '#64748b',
                      }}
                    />
                  </div>
                </div>
              ),
            )}
          </div>

          <div className="panel-footnote">
            {priorityTotal} complaints classified by priority
          </div>
        </div>

        <div className="panel sla-panel">
          <div className="panel-heading">
            <div>
              <h3>SLA performance</h3>
              <p>Response and resolution deadline breaches</p>
            </div>
            <span className="panel-tag">SLA</span>
          </div>

          <div className="sla-metric">
            <div>
              <span>Response breach rate</span>
              <strong>{analytics.sla.response_breach_rate_percent}%</strong>
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
              <strong>{analytics.sla.resolution_breach_rate_percent}%</strong>
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
              <h3>Workflow status distribution</h3>
              <p>Current complaint lifecycle</p>
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
                          width: `${statusTotal
                            ? (count / statusTotal) * 100
                            : 0}%`,
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
              <h3>Complaint category analysis</h3>
              <p>Volume across different issue types</p>
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
            <h3>Customer satisfaction analysis</h3>
            <p>Feedback submitted after complaint closure</p>
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
              Average rating from {surveyTotal} surveys
            </small>
          </div>

          <div className="rating-distribution">
            {Object.entries(
              analytics.customer_satisfaction.rating_distribution,
            )
              .sort((a, b) => Number(b[0]) - Number(a[0]))
              .map(([rating, count]) => (
                <div className="rating-row" key={rating}>
                  <span>{rating} ★</span>
                  <div className="rating-track">
                    <div
                      className="rating-fill"
                      style={{
                        width: `${surveyTotal
                          ? (count / surveyTotal) * 100
                          : 0}%`,
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
        <span>YottaFlex Complaint Management System · Analytics</span>
        <span>Last updated: {lastUpdated || 'Not available'}</span>
      </footer>
    </>
  )
}

export default Analytics
