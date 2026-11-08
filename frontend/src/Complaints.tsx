
import { useEffect, useState, type FormEvent } from 'react'
import CreateComplaintForm from './CreateComplaintForm'

const API_URL = 'http://127.0.0.1:8000'

const STATUSES = [
  'NEW',
  'CLASSIFIED',
  'ASSIGNED',
  'IN_PROGRESS',
  'PENDING_CUSTOMER',
  'RESOLVED',
  'CLOSED',
]

const PRIORITIES = ['P1', 'P2', 'P3', 'P4']

interface Complaint {
  complaint_id: string
  customer: {
    customer_id: string
    name: string
    email: string
  }
  category: string
  description: string
  channel: string
  sentiment: string
  severity: string
  priority: string
  status: string
  recurrence_count: number
  created_at: string | null
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
  skip: number
  limit: number
  complaints: Complaint[]
}

interface ComplaintDetail extends Omit<Complaint, 'customer'> {
  customer: {
    customer_id: string
    name: string
    email: string
    phone: string | null
    region: string | null
    is_vulnerable: boolean
  } | null
  order: {
    order_id: string
    total_amount: number
    payment_status: string
    order_status: string
  } | null
  updated_at: string | null
  messages: {
    message_id: string
    sender_type: string
    message_text: string
    channel: string
    is_internal: boolean
    created_at: string | null
  }[]
  assignment_history: {
    assignment_id: number
    agent_id: number | null
    team: string | null
    agent: string | null
    assigned_by: string
    reason: string | null
    is_current: boolean
    assigned_at: string | null
  }[]
  sla_clocks: {
    sla_id: string
    priority: string
    response_deadline: string | null
    resolution_deadline: string | null
    first_response_at: string | null
    resolved_at: string | null
    paused_at: string | null
    total_paused_seconds: number
    response_breached: boolean
    resolution_breached: boolean
  }[]
  resolutions: {
    resolution_id: string
    resolution_type: string
    description: string
    resolved_by: number
    resolved_at: string | null
    is_final: boolean
    survey: {
      rating: number
      feedback: string | null
      submitted_at: string | null
    } | null
  }[]
  priority_decisions: {
    decision_id: number
    calculated_score: number
    assigned_priority: string
    safety_override_applied: string | null
    explanation: string
    decided_at: string | null
  }[]
  events: {
    event_id: number
    event_type: string
    old_value: string | null
    new_value: string | null
    description: string | null
    performed_by: string
    created_at: string | null
  }[]
}

function formatDate(value: string | null) {
  if (!value) return '—'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return value

  return date.toLocaleString()
}

function readableStatus(status: string) {
  return status.replaceAll('_', ' ')
}

function ComplaintDetails({
  complaintId,
  onClose,
}: {
  complaintId: string
  onClose: () => void
}) {
    const [detail, setDetail] = useState<ComplaintDetail | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [actionLoading, setActionLoading] = useState(false)
    const [actionMessage, setActionMessage] = useState('')
    const [actionError, setActionError] = useState('')

  useEffect(() => {
    const controller = new AbortController()

    async function loadDetails() {
      try {
        setLoading(true)
        setError('')

        const response = await fetch(
          `${API_URL}/api/complaints/${encodeURIComponent(complaintId)}`,
          { signal: controller.signal },
        )

        if (!response.ok) {
          throw new Error(`Unable to load complaint (${response.status})`)
        }

        const data: ComplaintDetail = await response.json()
        setDetail(data)
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') return

        setError(
          err instanceof Error ? err.message : 'Unable to load complaint.',
        )
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    loadDetails()

    return () => controller.abort()
  }, [complaintId])

  async function refreshDetails() {
    const response = await fetch(
      `${API_URL}/api/complaints/${encodeURIComponent(complaintId)}`,
    )

    if (!response.ok) {
      throw new Error(`Unable to refresh complaint (${response.status})`)
    }

    const data: ComplaintDetail = await response.json()
    setDetail(data)
  }

  async function performAction(
    endpoint: string,
    method: 'PATCH' | 'POST',
    payload: Record<string, unknown>,
  ) {
    try {
      setActionLoading(true)
      setActionMessage('')
      setActionError('')

      const response = await fetch(
        `${API_URL}/api/complaints/${encodeURIComponent(complaintId)}/${endpoint}`,
        {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        },
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : `Request failed (${response.status})`,
        )
      }

      setActionMessage(data.message || 'Action completed successfully.')
      await refreshDetails()
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : 'The action could not be completed.',
      )
    } finally {
      setActionLoading(false)
    }
  }

  async function changeStatus(newStatus: string) {
    await performAction('status', 'PATCH', {
      new_status: newStatus,
      performed_by: 'Operations Analyst',
    })
  }

  async function resolveCurrentComplaint() {
    if (!detail) return

    const currentAssignment = detail.assignment_history.find(
      (assignment) => assignment.is_current,
    )

    if (!currentAssignment?.agent_id) {
      setActionError('Cannot resolve: no valid currently assigned agent ID was found.')
      return
    }

    const resolutionType = window.prompt(
      'Resolution type: REFUND, REPLACEMENT, REPAIR, INFORMATION or OTHER',
      'REFUND',
    )

    if (!resolutionType) return

    const allowedTypes = [
      'REFUND',
      'REPLACEMENT',
      'REPAIR',
      'INFORMATION',
      'OTHER',
    ]

    if (!allowedTypes.includes(resolutionType.trim().toUpperCase())) {
      setActionError('Invalid resolution type.')
      return
    }

    const description = window.prompt('Describe how the complaint was resolved:')

    if (!description || description.trim().length < 10) {
      setActionError('Please enter a resolution description of at least 10 characters.')
      return
    }

    await performAction('resolve', 'POST', {
      resolution_type: resolutionType.trim().toUpperCase(),
      resolution_description: description.trim(),
      resolved_by: currentAssignment.agent_id,
    })
  }

  async function reopenCurrentComplaint() {
    const reason = window.prompt('Why is this complaint being reopened?')

    if (!reason || reason.trim().length < 10) {
      setActionError('Please enter a reopening reason of at least 10 characters.')
      return
    }

    await performAction('reopen', 'POST', {
      reason: reason.trim(),
      performed_by: 'Operations Analyst',
    })
  }

  return (
    <div className="complaint-modal-backdrop" onClick={onClose}>
      <section
        className="complaint-detail-modal"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="complaint-detail-header">
          <div>
            <span className="detail-eyebrow">COMPLAINT DETAILS</span>
            <h2>{complaintId}</h2>
          </div>

          <button
            className="detail-close-button"
            onClick={onClose}
            aria-label="Close complaint details"
          >
            ×
          </button>
        </div>

        {loading && (
          <div className="complaint-detail-loading">
            Loading complaint details...
          </div>
        )}

        {error && <div className="complaint-error">{error}</div>}

        {detail && !loading && (
          <div className="complaint-detail-body">
            <div className="detail-summary">
              <div>
                <span>Priority</span>
                <strong className={`priority-badge ${detail.priority.toLowerCase()}`}>
                  {detail.priority}
                </strong>
              </div>

              <div>
                <span>Status</span>
                <strong className="status-badge">
                  {readableStatus(detail.status)}
                </strong>
              </div>

              <div>
                <span>Severity</span>
                <strong>{detail.severity}</strong>
              </div>
            </div>

            <section className="workflow-actions">
              <h3>Workflow actions</h3>

              <div className="workflow-button-row">
                {detail.status === 'ASSIGNED' && (
                  <button
                    type="button"
                    disabled={actionLoading}
                    onClick={() => changeStatus('IN_PROGRESS')}
                  >
                    Start work
                  </button>
                )}

                {detail.status === 'IN_PROGRESS' && (
                  <>
                    <button
                      type="button"
                      disabled={actionLoading}
                      onClick={() => changeStatus('PENDING_CUSTOMER')}
                    >
                      Await customer
                    </button>

                    <button
                      type="button"
                      disabled={actionLoading}
                      onClick={resolveCurrentComplaint}
                    >
                      Resolve complaint
                    </button>
                  </>
                )}

                {detail.status === 'PENDING_CUSTOMER' && (
                  <button
                    type="button"
                    disabled={actionLoading}
                    onClick={() => changeStatus('IN_PROGRESS')}
                  >
                    Resume work
                  </button>
                )}

                {detail.status === 'RESOLVED' && (
                  <>
                    <button
                      type="button"
                      disabled={actionLoading}
                      onClick={() => changeStatus('CLOSED')}
                    >
                      Close complaint
                    </button>

                    <button
                      type="button"
                      disabled={actionLoading}
                      onClick={reopenCurrentComplaint}
                    >
                      Reopen complaint
                    </button>
                  </>
                )}

                {detail.status === 'CLOSED' && (
                  <p>This complaint is closed. No further actions are available.</p>
                )}
              </div>

              {actionLoading && (
                <p className="workflow-loading">Processing action...</p>
              )}

              {actionMessage && (
                <p className="workflow-success">{actionMessage}</p>
              )}

              {actionError && (
                <p className="workflow-error">{actionError}</p>
              )}
            </section>

            <section className="detail-section">
              <h3>Complaint information</h3>
              <p className="detail-description">{detail.description}</p>

              <div className="detail-info-grid">
                <div>
                  <span>Category</span>
                  <strong>{detail.category || '—'}</strong>
                </div>
                <div>
                  <span>Channel</span>
                  <strong>{detail.channel}</strong>
                </div>
                <div>
                  <span>Sentiment</span>
                  <strong>{detail.sentiment}</strong>
                </div>
                <div>
                  <span>Recurrence count</span>
                  <strong>{detail.recurrence_count}</strong>
                </div>
                <div>
                  <span>Created</span>
                  <strong>{formatDate(detail.created_at)}</strong>
                </div>
                <div>
                  <span>Updated</span>
                  <strong>{formatDate(detail.updated_at)}</strong>
                </div>
              </div>
            </section>

            <section className="detail-section">
              <h3>Customer information</h3>

              {detail.customer ? (
                <div className="detail-info-grid">
                  <div>
                    <span>Name</span>
                    <strong>{detail.customer.name}</strong>
                  </div>
                  <div>
                    <span>Customer ID</span>
                    <strong>{detail.customer.customer_id}</strong>
                  </div>
                  <div>
                    <span>Email</span>
                    <strong>{detail.customer.email}</strong>
                  </div>
                  <div>
                    <span>Phone</span>
                    <strong>{detail.customer.phone || '—'}</strong>
                  </div>
                  <div>
                    <span>Region</span>
                    <strong>{detail.customer.region || '—'}</strong>
                  </div>
                  <div>
                    <span>Vulnerable customer</span>
                    <strong>
                      {detail.customer.is_vulnerable ? 'Yes' : 'No'}
                    </strong>
                  </div>
                </div>
              ) : (
                <p>Customer information unavailable.</p>
              )}
            </section>

            <section className="detail-section">
              <h3>Order information</h3>

              {detail.order ? (
                <div className="detail-info-grid">
                  <div>
                    <span>Order ID</span>
                    <strong>{detail.order.order_id}</strong>
                  </div>
                  <div>
                    <span>Order value</span>
                    <strong>
                      ₹{detail.order.total_amount.toLocaleString('en-IN')}
                    </strong>
                  </div>
                  <div>
                    <span>Payment status</span>
                    <strong>{detail.order.payment_status}</strong>
                  </div>
                  <div>
                    <span>Order status</span>
                    <strong>{detail.order.order_status}</strong>
                  </div>
                </div>
              ) : (
                <p>No order linked to this complaint.</p>
              )}
            </section>

            <section className="detail-section">
              <h3>Current assignment</h3>

              {detail.assignment_history.length > 0 ? (
                <div className="detail-history-list">
                  {detail.assignment_history.map((assignment) => (
                    <div
                      className="detail-history-item"
                      key={assignment.assignment_id}
                    >
                      <strong>
                        {assignment.team || 'Unassigned team'}
                        {assignment.is_current && (
                          <span className="current-label">CURRENT</span>
                        )}
                      </strong>
                      <p>Agent: {assignment.agent || 'Unassigned'}</p>
                      <p>Assigned by: {assignment.assigned_by}</p>
                      <p>Reason: {assignment.reason || '—'}</p>
                      <small>{formatDate(assignment.assigned_at)}</small>
                    </div>
                  ))}
                </div>
              ) : (
                <p>No assignment history available.</p>
              )}
            </section>

            <section className="detail-section">
              <h3>SLA history</h3>

              {detail.sla_clocks.length > 0 ? (
                detail.sla_clocks.map((sla) => (
                  <div className="detail-history-item" key={sla.sla_id}>
                    <strong>{sla.sla_id}</strong>
                    <p>
                      Response deadline: {formatDate(sla.response_deadline)}
                    </p>
                    <p>
                      Resolution deadline:{' '}
                      {formatDate(sla.resolution_deadline)}
                    </p>
                    <p>
                      Response breached:{' '}
                      {sla.response_breached ? 'Yes' : 'No'}
                    </p>
                    <p>
                      Resolution breached:{' '}
                      {sla.resolution_breached ? 'Yes' : 'No'}
                    </p>
                    <p>
                      Paused: {sla.paused_at ? 'Yes' : 'No'}
                    </p>
                    <p>
                      Total paused time: {sla.total_paused_seconds} seconds
                    </p>
                  </div>
                ))
              ) : (
                <p>No SLA history available.</p>
              )}
            </section>

            <section className="detail-section">
              <h3>Messages ({detail.messages.length})</h3>

              {detail.messages.length > 0 ? (
                detail.messages.map((message) => (
                  <div className="detail-history-item" key={message.message_id}>
                    <div className="message-heading">
                      <strong>{message.sender_type}</strong>
                      <span>
                        {message.is_internal ? 'INTERNAL' : 'PUBLIC'}
                      </span>
                    </div>
                    <p>{message.message_text}</p>
                    <small>
                      {message.channel} · {formatDate(message.created_at)}
                    </small>
                  </div>
                ))
              ) : (
                <p>No messages available.</p>
              )}
            </section>

            <section className="detail-section">
              <h3>Resolution history ({detail.resolutions.length})</h3>

              {detail.resolutions.length > 0 ? (
                detail.resolutions.map((resolution) => (
                  <div
                    className="detail-history-item"
                    key={resolution.resolution_id}
                  >
                    <strong>
                      {resolution.resolution_type}
                      {resolution.is_final && (
                        <span className="current-label">FINAL</span>
                      )}
                    </strong>
                    <p>{resolution.description}</p>
                    <small>{formatDate(resolution.resolved_at)}</small>

                    {resolution.survey && (
                      <p>
                        Customer rating: {resolution.survey.rating}/5
                        {resolution.survey.feedback
                          ? ` — ${resolution.survey.feedback}`
                          : ''}
                      </p>
                    )}
                  </div>
                ))
              ) : (
                <p>No resolution recorded yet.</p>
              )}
            </section>

            <section className="detail-section">
              <h3>Priority decisions ({detail.priority_decisions.length})</h3>

              {detail.priority_decisions.map((decision) => (
                <div
                  className="detail-history-item"
                  key={decision.decision_id}
                >
                  <strong>
                    {decision.assigned_priority} · Score{' '}
                    {decision.calculated_score}
                  </strong>
                  <p>{decision.explanation}</p>
                  <p>
                    Safety override:{' '}
                    {decision.safety_override_applied || 'Not recorded'}
                  </p>
                  <small>{formatDate(decision.decided_at)}</small>
                </div>
              ))}
            </section>

            <section className="detail-section">
              <h3>Event history ({detail.events.length})</h3>

              {detail.events.length > 0 ? (
                detail.events.map((event) => (
                  <div className="detail-history-item" key={event.event_id}>
                    <strong>{readableStatus(event.event_type)}</strong>
                    <p>{event.description || '—'}</p>
                    <p>Performed by: {event.performed_by}</p>
                    <small>{formatDate(event.created_at)}</small>
                  </div>
                ))
              ) : (
                <p>No events recorded.</p>
              )}
            </section>
          </div>
        )}
      </section>
    </div>
  )
}

function Complaints() {
  const [complaints, setComplaints] = useState<Complaint[]>([])
  const [total, setTotal] = useState(0)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [priority, setPriority] = useState('')
  const [page, setPage] = useState(0)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [refreshCount, setRefreshCount] = useState(0)
  const [creationMessage, setCreationMessage] = useState('')

  const pageSize = 10

  useEffect(() => {
    const controller = new AbortController()

    async function loadComplaints() {
      try {
        setLoading(true)
        setError('')

        const params = new URLSearchParams({
          skip: String(page * pageSize),
          limit: String(pageSize),
        })

        if (search) params.set('search', search)
        if (status) params.set('status', status)
        if (priority) params.set('priority', priority)

        const response = await fetch(
          `${API_URL}/api/complaints?${params.toString()}`,
          { signal: controller.signal },
        )

        if (!response.ok) {
          throw new Error(`API returned status ${response.status}`)
        }

        const data: ComplaintListResponse = await response.json()

        setComplaints(data.complaints)
        setTotal(data.total)
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') return

        setError(
          err instanceof Error ? err.message : 'Unable to load complaints.',
        )
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    loadComplaints()

    return () => controller.abort()
  }, [search, status, priority, page, refreshCount])

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPage(0)
    setSearch(searchInput.trim())
  }

  function handleStatusChange(value: string) {
    setStatus(value)
    setPage(0)
  }

  function handlePriorityChange(value: string) {
    setPriority(value)
    setPage(0)
  }

  function clearFilters() {
    setSearchInput('')
    setSearch('')
    setStatus('')
    setPriority('')
    setPage(0)
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="complaints-page">
      <div className="complaints-page-heading">
  <div>
    <h2>Complaint records</h2>
    <p>Search, filter and inspect customer complaints.</p>
  </div>

  <div className="complaint-heading-actions">
    <span className="complaint-total">
      {total} TOTAL RECORDS
    </span>

    <button
      type="button"
      className="complaint-search-button"
      onClick={() => {
        setCreationMessage('')
        setShowCreateForm(true)
      }}
    >
      + Create complaint
    </button>
  </div>
</div>

{creationMessage && (
  <div className="workflow-success">
    {creationMessage}
  </div>
)}

      <section className="complaint-filter-panel">
        <form className="complaint-search-form" onSubmit={handleSearch}>
          <input
            type="search"
            placeholder="Search complaint ID, customer, email or description..."
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
          />

          <button type="submit" className="complaint-search-button">
            Search
          </button>
        </form>

        <div className="complaint-filter-row">
          <label>
            Status
            <select
              value={status}
              onChange={(event) => handleStatusChange(event.target.value)}
            >
              <option value="">All statuses</option>
              {STATUSES.map((item) => (
                <option value={item} key={item}>
                  {readableStatus(item)}
                </option>
              ))}
            </select>
          </label>

          <label>
            Priority
            <select
              value={priority}
              onChange={(event) => handlePriorityChange(event.target.value)}
            >
              <option value="">All priorities</option>
              {PRIORITIES.map((item) => (
                <option value={item} key={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>

          <button
            type="button"
            className="clear-filters-button"
            onClick={clearFilters}
          >
            Clear filters
          </button>
        </div>
      </section>

      {error && (
        <div className="complaint-error">
          {error}
          <button type="button" onClick={() => setPage(page)}>
            Retry
          </button>
        </div>
      )}

      <section className="complaint-table-panel">
        <div className="complaint-table-heading">
          <div>
            <h3>All complaints</h3>
            <p>
              Showing {complaints.length ? page * pageSize + 1 : 0}–
              {Math.min((page + 1) * pageSize, total)} of {total} records
            </p>
          </div>

          <span className="table-live-label">LIVE DATABASE</span>
        </div>

        <div className="complaint-table-wrapper">
          <table className="complaint-table">
            <thead>
              <tr>
                <th>Complaint</th>
                <th>Customer</th>
                <th>Category</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Assigned team</th>
                <th>Created</th>
              </tr>
            </thead>

            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="complaint-empty">
                    Loading complaints...
                  </td>
                </tr>
              ) : complaints.length === 0 ? (
                <tr>
                  <td colSpan={7} className="complaint-empty">
                    No complaints match your search or filters.
                  </td>
                </tr>
              ) : (
                complaints.map((complaint) => (
                  <tr
                    key={complaint.complaint_id}
                    className="complaint-clickable-row"
                    onClick={() => setSelectedId(complaint.complaint_id)}
                  >
                    <td>
                      <strong>{complaint.complaint_id}</strong>
                      <small>{complaint.channel}</small>
                    </td>

                    <td>
                      <strong>{complaint.customer.name}</strong>
                      <small>{complaint.customer.email}</small>
                    </td>

                    <td>{complaint.category}</td>

                    <td>
                      <span
                        className={`priority-badge ${complaint.priority.toLowerCase()}`}
                      >
                        {complaint.priority}
                      </span>
                    </td>

                    <td>
                      <span className="status-badge">
                        {readableStatus(complaint.status)}
                      </span>
                    </td>

                    <td>
                      {complaint.assignment?.team || 'Unassigned'}
                      <small>
                        {complaint.assignment?.agent || 'No agent'}
                      </small>
                    </td>

                    <td>{formatDate(complaint.created_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="complaint-pagination">
          <span>
            Page {totalPages === 0 ? 0 : page + 1} of {totalPages}
          </span>

          <div>
            <button
              type="button"
              disabled={page === 0 || loading}
              onClick={() => setPage((current) => current - 1)}
            >
              Previous
            </button>

            <button
              type="button"
              disabled={page + 1 >= totalPages || loading}
              onClick={() => setPage((current) => current + 1)}
            >
              Next
            </button>
          </div>
        </div>
      </section>

      {selectedId && (
        <ComplaintDetails
          complaintId={selectedId}
          onClose={() => setSelectedId(null)}
        />
      )}

{showCreateForm && (
  <CreateComplaintForm
    onCancel={() => setShowCreateForm(false)}
    onCreated={(complaintId) => {
      setShowCreateForm(false)
      setSearchInput('')
      setSearch('')
      setStatus('')
      setPriority('')
      setPage(0)
      setCreationMessage(
        `Complaint ${complaintId} created successfully.`,
      )
      setRefreshCount((current) => current + 1)
    }}
  />
)}

    </div>
  )
}

export default Complaints
