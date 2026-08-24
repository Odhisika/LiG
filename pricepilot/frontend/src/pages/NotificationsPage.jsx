import { useEffect, useState } from "react";
import { notificationsApi } from "../api/domains";
import { Badge, EmptyState, ErrorAlert, Spinner } from "../components/ui";

const EVENT_TYPES = ["product_updated", "out_of_stock", "scrape_failed", "new_products_found"];

export default function NotificationsPage() {
  const [events, setEvents] = useState([]);
  const [eventType, setEventType] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    notificationsApi
      .list(eventType ? { event_type: eventType } : {})
      .then(setEvents)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [eventType]);

  return (
    <div>
      <div className="page-header">
        <h1>Notifications</h1>
      </div>
      <ErrorAlert message={error} />

      <div className="filter-row">
        <label className="muted" style={{ fontSize: "0.85rem" }}>
          Type:
        </label>
        <select value={eventType} onChange={(e) => setEventType(e.target.value)}>
          <option value="">All</option>
          {EVENT_TYPES.map((t) => (
            <option key={t} value={t}>
              {t.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <Spinner />
      ) : events.length === 0 ? (
        <EmptyState>No notification events yet.</EmptyState>
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Product / Supplier</th>
                  <th>Sent</th>
                  <th>When</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev) => (
                  <tr key={ev.id}>
                    <td>
                      <Badge value={ev.event_type} />
                    </td>
                    <td>{ev.product_name || ev.supplier_name || "—"}</td>
                    <td>
                      <Badge value={String(ev.sent)} />
                    </td>
                    <td className="muted">{new Date(ev.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      <p className="muted" style={{ fontSize: "0.8rem" }}>
        Unsent events are batched into one digest email per 15-minute cycle rather than sent
        individually.
      </p>
    </div>
  );
}
