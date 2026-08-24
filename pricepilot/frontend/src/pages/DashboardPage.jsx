import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { dashboardApi, pricingApi } from "../api/domains";
import { ErrorAlert, Spinner, SuccessAlert } from "../components/ui";

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
                {summary.average_profit !== null ? summary.average_profit : "—"}
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
                rule or a manual selling price. Takes effect in your store on the
                next sync.
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
                  {savingMarkup ? "Saving…" : "Save markup"}
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

          <div className="card">
            <h2>Today's activity</h2>
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
            <p className="muted" style={{ marginTop: 12, marginBottom: 0, fontSize: "0.8rem" }}>
              These populate once the scheduler has been running for a while — see History and
              Notifications for the full activity log in the meantime.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
