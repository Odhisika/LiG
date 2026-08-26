import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { dashboardApi, pricingApi } from "../api/domains";
import { Badge, ErrorAlert, Spinner, SuccessAlert } from "../components/ui";

const EVENT_ICONS = {
  check_ok: "\u2713",
  price_change: "\u2195",
  stock_change: "\u2194",
  scrape_failed: "\u2717",
  removed: "\u2298",
  store_synced: "\u2192",
  store_deleted: "\u2715",
  discovered: "\u2605",
  imported: "\u2b07",
  status_change: "\u21c4",
};

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [markup, setMarkup] = useState("");
  const [savingMarkup, setSavingMarkup] = useState(false);
  const [markupMessage, setMarkupMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardApi
      .summary()
      .then((data) => {
        setSummary(data);
        setMarkup(data.default_markup ?? "");
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleSaveMarkup(e) {
    e.preventDefault();
    setSavingMarkup(true);
    setMarkupMessage("");
    try {
      const result = await pricingApi.setDefaultMarkup(Number(markup));
      setSummary((s) => ({ ...s, default_markup: result.markup_percent }));
      setMarkupMessage(
        `Saved. Applies to ${result.affected_products} product${
          result.affected_products === 1 ? "" : "s"
        } without their own pricing rule.`
      );
    } catch (err) {
      setMarkupMessage("");
      setError(err.message);
    } finally {
      setSavingMarkup(false);
    }
  }

  if (loading) return <Spinner />;

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
      </div>
      <ErrorAlert message={error} />

      {summary && (
        <>
          <div className="grid" style={{ marginBottom: 20 }}>
            <div className="stat">
              <div className="label">Products monitored</div>
              <div className="value">{summary.products_monitored}</div>
            </div>
            <div className="stat">
              <div className="label">Suppliers</div>
              <div className="value">{summary.suppliers_count}</div>
            </div>
            <div className="stat">
              <div className="label">Average profit</div>
              <div className="value">
                {summary.average_profit !== null ? summary.average_profit : "\u2014"}
              </div>
            </div>
            <div className="stat">
              <div className="label">Checks today</div>
              <div className="value">{summary.todays_checks}</div>
            </div>
          </div>

          <div className="grid" style={{ marginBottom: 20, alignItems: "flex-start" }}>
            <div className="card">
              <h2>Default markup</h2>
              <p className="muted" style={{ fontSize: "0.85rem", marginTop: 0 }}>
                Adds a percentage to products that don&apos;t have their own pricing
                rule or a manual selling price. Saves are pushed to your store
                immediately.
              </p>
              <form onSubmit={handleSaveMarkup} style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <input
                  type="number"
                  min="0"
                  step="0.5"
                  value={markup}
                  onChange={(e) => setMarkup(e.target.value)}
                  placeholder="0.0"
                  style={{ width: 110 }}
                  required
                />
                <span>%</span>
                <button type="submit" className="btn btn-primary" disabled={savingMarkup}>
                  {savingMarkup ? "Saving\u2026" : "Save markup"}
                </button>
              </form>
              {markupMessage && (
                <SuccessAlert message={markupMessage} />
              )}
            </div>

            <div className="card" style={{ flex: 2 }}>
              <h2>Products by category</h2>
              {summary.products_by_category.length === 0 ? (
                <p className="muted" style={{ marginBottom: 0 }}>
                  No products categorized yet.
                </p>
              ) : (
                <div className="table-wrap">
                  <table>
                    <tbody>
                      {summary.products_by_category.map(({ category, count }) => (
                        <tr key={category}>
                          <td>
                            <Link to={`/products?category=${encodeURIComponent(category)}`}>
                              {category}
                            </Link>
                          </td>
                          <td style={{ textAlign: "right", width: 60 }}>{count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          <div className="card">
            <h2>Products by status</h2>
            <div className="grid">
              {Object.entries(summary.products_by_status).map(([status, count]) => (
                <div className="stat" key={status}>
                  <div className="label">{status.replace(/_/g, " ")}</div>
                  <div className="value">{count}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid" style={{ marginBottom: 0, alignItems: "flex-start" }}>
            <div className="card" style={{ flex: 1 }}>
              <h2>Today&apos;s activity</h2>
              <div className="grid">
                <div className="stat">
                  <div className="label">Products changed</div>
                  <div className="value">{summary.products_changed_today}</div>
                </div>
                <div className="stat">
                  <div className="label">Stock changes</div>
                  <div className="value">{summary.stock_changes_today}</div>
                </div>
                <div className="stat">
                  <div className="label">Failed scrapes</div>
                  <div className="value">{summary.failed_scrapes_today}</div>
                </div>
              </div>
            </div>

            <div className="card" style={{ flex: 1.5 }}>
              <h2>Recent activity</h2>
              {summary.recent_activity.length === 0 ? (
                <p className="muted" style={{ marginBottom: 0, fontSize: "0.85rem" }}>
                  No activity yet \u2014 this fills in once the scheduler runs.
                </p>
              ) : (
                <div className="activity-feed">
                  {summary.recent_activity.map((ev) => (
                    <div className="activity-item" key={ev.id}>
                      <span className="activity-icon">
                        {EVENT_ICONS[ev.event_type] || "\u2022"}
                      </span>
                      <div className="activity-body">
                        <div>
                          <Badge value={ev.event_type} />
                          {ev.product_name && (
                            <span className="activity-target"> {ev.product_name}</span>
                          )}
                          {ev.supplier_name && !ev.product_name && (
                            <span className="activity-target"> {ev.supplier_name}</span>
                          )}
                        </div>
                        <div className="activity-meta muted">
                          {timeAgo(ev.created_at)}
                          {ev.payload?.action && ` \u00b7 ${ev.payload.action}`}
                          {ev.payload?.old_price && ev.payload?.new_price && (
                            <> \u00b7 {ev.payload.old_price} \u2192 {ev.payload.new_price}</>
                          )}
                          {ev.payload?.reason && (
                            <> \u00b7 {ev.payload.reason}</>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {summary.recent_activity.length > 0 && (
                <div style={{ marginTop: 10 }}>
                  <Link to="/activity" style={{ fontSize: "0.85rem" }}>
                    View all activity \u2192
                  </Link>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
