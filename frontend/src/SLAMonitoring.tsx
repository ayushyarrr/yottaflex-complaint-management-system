
import { useCallback, useEffect, useState } from 'react'

const API_URL = 'http://127.0.0.1:8000'

interface SLAComplaint {
  complaint_id: string
  customer: {
    customer_id: string
    name: string
    email: string
  }
  category: string
  priority: string
  status: string
  assignment: {
    team: string | null
    agent: string | null
  } | null
  sla: {
    response_deadline: string | null
    resolution_deadline: string | null
    response_breached: boolean
    resolution_breached: boolean
    paused: boolean
  } | null
}

interface ComplaintListResponse {
  total: number
  complaints: SLAComplaint[]
}

function formatDeadline(value: string | null) {
  if (!value) return 'Not available'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return value

  return date.toLocaleString()
}

function SLAMonitoring() {
  const [complaints, setComplaints] = useState<SLAComplaint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [lastUpdated, setLastUpdated] = useState('')
  const [showAll, setShowAll] = useState(false)

  const loadSLAData = useCallback(async () => {
    try {
      setLoading(true)
      setError('')

      const response = await fetch(
        `${API_URL}/api/complaints?skip=0&limit=200`,
      )

      if (!response.ok) {
        throw new Error(`API returned status ${response.status}`)
      }

      const data: ComplaintListResponse = await response.json()

      setComplaints(data.complaints)
      setLastUpdated(new Date().toLocaleTimeString())
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to load SLA information.',
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadSLAData()
  }, [loadSLAData])

  const activeComplaints = complaints.filter(
    (complaint) =>
      complaint.status !== 'RESOLVED' &&
      complaint.status !== 'CLOSED' &&
      complaint.sla !== null,
  )

  const pausedCount = activeComplaints.filter(
    (complaint) => complaint.sla?.paused,
  ).length

  const responseBreaches = complaints.filter(
    (complaint) => complaint.sla?.response_breached,
  ).length

  const resolutionBreaches = complaints.filter(
    (complaint) => complaint.sla?.resolution_breached,
  ).length

  const displayedComplaints = showAll
    ? complaints.filter((complaint) => complaint.sla !== null)
    : activeComplaints

  return (
    <div className="sla-page">
      <section className="sla-page-heading">
        <div>
          <div className="sla-breadcrumb">Workspace / SLA Monitoring</div>
          <h2>SLA Monitoring</h2>
          <p>
            Track response and resolution deadlines across customer complaints.
          </p>
        </div>

        <button
          className="sla-refresh-button"
          onClick={loadSLAData}
          disabled={loading}
        >
          ↻ {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </section>

      {error && (
        <div className="sla-error">
          <strong>Unable to load SLA data.</strong>
          <span>{error}</span>
          <button onClick={loadSLAData}>Try again</button>
        </div>
      )}

      <section className="sla-summary-grid">
        <div className="sla-summary-card">
          <span>Active SLA records</span>
          <strong>{activeComplaints.length}</strong>
          <small>Complaints not yet resolved or closed</small>
        </div>

        <div className="sla-summary-card">
          <span>Paused clocks</span>
          <strong>{pausedCount}</strong>
          <small>Waiting for customer information</small>
        </div>

        <div className="sla-summary-card">
          <span>Response breaches</span>
          <strong>{responseBreaches}</strong>
          <small>Recorded across available SLA records</small>
        </div>

        <div className="sla-summary-card">
          <span>Resolution breaches</span>
          <strong>{resolutionBreaches}</strong>
          <small>Recorded across available SLA records</small>
        </div>
      </section>

      <section className="sla-table-panel">
        <div className="sla-table-heading">
          <div>
            <h3>Complaint SLA records</h3>
            <p>
              {showAll
                ? 'All complaints with an SLA record'
                : 'Currently active complaints'}
            </p>
          </div>

          <button
            className="sla-view-toggle"
            onClick={() => setShowAll((current) => !current)}
          >
            {showAll ? 'Show active only' : 'Show all records'}
          </button>
        </div>

        {loading && complaints.length === 0 ? (
          <div className="sla-empty-state">Loading SLA records...</div>
        ) : displayedComplaints.length === 0 ? (
          <div className="sla-empty-state">
            No SLA records found for this view.
          </div>
        ) : (
          <div className="sla-table-wrapper">
            <table className="sla-table">
              <thead>
                <tr>
                  <th>Complaint</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Assigned team / agent</th>
                  <th>Response deadline</th>
                  <th>Resolution deadline</th>
                  <th>SLA condition</th>
                </tr>
              </thead>

              <tbody>
                {displayedComplaints.map((complaint) => {
                  const conditions: string[] = []

                  if (complaint.sla?.paused) {
                    conditions.push('Paused')
                  }

                  if (complaint.sla?.response_breached) {
                    conditions.push('Response breached')
                  }

                  if (complaint.sla?.resolution_breached) {
                    conditions.push('Resolution breached')
                  }

                  if (conditions.length === 0) {
                    conditions.push('No recorded breach')
                  }

                  return (
                    <tr key={complaint.complaint_id}>
                      <td>
                        <strong>{complaint.complaint_id}</strong>
                        <small>{complaint.customer.name}</small>
                      </td>

                      <td>
                        <span className={`sla-priority ${complaint.priority.toLowerCase()}`}>
                          {complaint.priority}
                        </span>
                      </td>

                      <td>
                        <span className="sla-status">
                          {complaint.status.replaceAll('_', ' ')}
                        </span>
                      </td>

                      <td>
                        <strong>
                          {complaint.assignment?.team || 'Unassigned'}
                        </strong>
                        <small>
                          {complaint.assignment?.agent || 'No agent'}
                        </small>
                      </td>

                      <td>
                        {formatDeadline(
                          complaint.sla?.response_deadline ?? null,
                        )}
                        {complaint.sla?.response_breached && (
                          <small className="sla-breach-text">
                            Recorded breach
                          </small>
                        )}
                      </td>

                      <td>
                        {formatDeadline(
                          complaint.sla?.resolution_deadline ?? null,
                        )}
                        {complaint.sla?.resolution_breached && (
                          <small className="sla-breach-text">
                            Recorded breach
                          </small>
                        )}
                      </td>

                      <td>
                        <span
                          className={
                            conditions[0] === 'Paused'
                              ? 'sla-condition paused'
                              : conditions[0].includes('breached')
                                ? 'sla-condition breached'
                                : 'sla-condition normal'
                          }
                        >
                          {conditions.join(', ')}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <footer className="sla-page-footer">
        <span>
          Data source: Complaint Management API · Maximum 200 records per
          request
        </span>
        <span>
          Last updated: {lastUpdated || 'Not yet refreshed'}
        </span>
      </footer>
    </div>
  )
}

export default SLAMonitoring
