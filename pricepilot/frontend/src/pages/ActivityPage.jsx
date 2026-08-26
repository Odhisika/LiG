import { useEffect, useState } from "react";
import { dashboardApi } from "../api/domains";
import { Badge, EmptyState, ErrorAlert, Spinner } from "../components/ui";

const EVENT_TYPES = [
  "check_ok",
  "price_change",
  "stock_change",
  "scrape_failed",
  "removed",
  "store_synced",
  "store_deleted",
  "discovered",
  "imported",
  "status_change",
];

function payloadSummary(payload) {
  if (!payload || Object.keys(payload).length === 0) return null;
  const parts = [];
  if (payload.old_price && payload.new_price) {
    parts.push(`${payload.old_price} \u2192 ${payload.new_price}`);
  }
  if (payload.old_stock !== undefined && payload.new_stock !== undefined) {
    parts.push(`stock: ${payload.old_stock} \u2192 ${payload.new_stock}`);
  }
  if (payload.action) parts.push(payload.action);
  if (payload.reason) parts.push(payload.reason);
  if (payload.old_status && payload.new_status) {
    parts.push(`${payload.old_status} \u2192 ${payload.new_status}`);
  }
  if (payload.stock !== undefined && payload.threshold !== undefined) {
    parts.push(`${payload.stock} left (threshold: ${payload.threshold})`);
  }
  if (payload.url) parts.push(payload.url);
  return parts.length > 0 ? parts.join(" \u00b7 ") : null;
}

export default function ActivityPage() {
  const [events, setEvents] = useState([]);
  const [page, setPage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [eventType, setEventType] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  function load(url) {
    setLoading(true);
    setError("");
    const params = {};
    if (eventType) params.event_type = eventType;
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;

    const fetchFn = url
      ? () => fetch(url).then((r) => r.json())
      : () => dashboardApi.activity(params);

    fetchFn()
      .then((data) => {
        const result = data?.data ?? data;
        setEvents(result?.results ?? []);
        setPage(result ?? null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    setPage(null);
    load();
  }, [eventType, dateFrom, dateTo]);

  return (
    <div>
      <div className="page-header">
        <h1>Activity</h1>
      </div>
      <ErrorAlert message={error} />

      <div className="filter-row">
        <label className="muted" style={{ fontSize: "0.85rem" }}>Type:</label>
        <select value={eventType} onChange={(e) => setEventType(e.target.value)}>
          <option value="">All events</option>
          {EVENT_TYPES.map((t) => (
            <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
          ))}
        </select>

        <label className="muted" style={{ fontSize: "0.85rem" }}>From:</label>
        <input
          type="date"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
        />

        <label className="muted" style={{ fontSize: "0.85rem" }}>To:</label>
        <input
          type="date"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
        />
      </div>

      {loading ? (
        <Spinner />
      ) : events.length === 0 ? (
        <EmptyState>No activity events found.</EmptyState>
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th style={{ width: 140 }}>When</th>
                  <th style={{ width: 160 }}>Event</th>
                  <th>Product</th>
                  <th>Supplier</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev) => (
                  <tr key={ev.id}>
                    <td className="muted">{new Date(ev.created_at).toLocaleString()}</td>
                    <td><Badge value={ev.event_type} /></td>
                    <td>{ev.product_name || "\u2014"}</td>
                    <td>{ev.supplier_name || "\u2014"}</td>
                    <td className="muted" style={{ fontSize: "0.82rem" }}>
                      {payloadSummary(ev.payload) || "\u2014"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="activity-pagination">
            {page?.previous && (
              <button
                className="btn btn-sm"
                onClick={() => load(page.previous)}
              >
                Previous
              </button>
            )}
            {page?.next && (
              <button
                className="btn btn-sm"
                onClick={() => load(page.next)}
              >
                Next
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
