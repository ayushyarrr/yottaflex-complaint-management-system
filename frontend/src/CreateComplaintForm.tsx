
import { useState, type FormEvent } from 'react'

const API_URL = 'http://127.0.0.1:8000'

interface CreateComplaintFormProps {
  onCreated: (complaintId: string) => void
  onCancel: () => void
}

function CreateComplaintForm({
  onCreated,
  onCancel,
}: CreateComplaintFormProps) {
  const [customerId, setCustomerId] = useState('')
  const [orderId, setOrderId] = useState('')
  const [productIds, setProductIds] = useState('')
  const [description, setDescription] = useState('')
  const [channel, setChannel] = useState('WEB')
  const [sentiment, setSentiment] = useState('NEUTRAL')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')

    const payload = {
      customer_id: customerId.trim(),
      order_id: orderId.trim() || null,
      product_ids: productIds.trim()
        ? productIds.split(',').map((id) => id.trim()).filter(Boolean)
        : null,
      description: description.trim(),
      channel,
      sentiment,
    }

    try {
      setSubmitting(true)

      const response = await fetch(`${API_URL}/api/complaints`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      const data = await response.json()

      if (!response.ok) {
        const detail = data.detail
        const message = Array.isArray(detail)
          ? detail.map((item: { msg?: string }) => item.msg || 'Invalid input').join('; ')
          : typeof detail === 'string'
            ? detail
            : `Request failed (${response.status})`

        throw new Error(message)
      }

      onCreated(data.complaint_id)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to create the complaint.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="create-complaint-backdrop">
      <section className="create-complaint-modal">
        <div className="create-complaint-header">
          <div>
            <span className="detail-eyebrow">NEW CUSTOMER CASE</span>
            <h2>Create complaint</h2>
            <p>Enter the complaint information to start the workflow.</p>
          </div>

          <button
            type="button"
            className="detail-close-button"
            onClick={onCancel}
            aria-label="Close form"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="create-complaint-form">
          <label>
            Customer ID *
            <input
              value={customerId}
              onChange={(event) => setCustomerId(event.target.value)}
              placeholder="e.g. CUS-000001"
              required
              maxLength={20}
            />
          </label>

          <label>
            Order ID
            <input
              value={orderId}
              onChange={(event) => setOrderId(event.target.value)}
              placeholder="e.g. ORD-2026-000001 (optional)"
              maxLength={30}
            />
          </label>

          <label>
            Product IDs
            <input
              value={productIds}
              onChange={(event) => setProductIds(event.target.value)}
              placeholder="e.g. PRD-000001, PRD-000002 (optional)"
            />
            <small>Separate multiple product IDs with commas.</small>
          </label>

          <label>
            Complaint description *
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Describe the customer's issue in detail..."
              minLength={10}
              maxLength={5000}
              rows={5}
              required
            />
          </label>

          <div className="create-complaint-fields">
            <label>
              Channel *
              <select
                value={channel}
                onChange={(event) => setChannel(event.target.value)}
              >
                <option value="WEB">Web</option>
                <option value="EMAIL">Email</option>
                <option value="PHONE">Phone</option>
                <option value="CHAT">Chat</option>
              </select>
            </label>

            <label>
              Customer sentiment *
              <select
                value={sentiment}
                onChange={(event) => setSentiment(event.target.value)}
              >
                <option value="STRONGLY NEGATIVE">Strongly negative</option>
                <option value="NEGATIVE">Negative</option>
                <option value="NEUTRAL">Neutral</option>
                <option value="POSITIVE">Positive</option>
              </select>
            </label>
          </div>

          {error && (
            <div className="complaint-error">
              {error}
            </div>
          )}

          <div className="create-complaint-actions">
            <button
              type="button"
              className="detail-secondary-button"
              onClick={onCancel}
              disabled={submitting}
            >
              Cancel
            </button>

            <button
              type="submit"
              className="complaint-search-button"
              disabled={submitting}
            >
              {submitting ? 'Creating...' : 'Create complaint'}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}

export default CreateComplaintForm
