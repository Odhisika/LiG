import { useEffect, useState } from "react";
import { analyticsApi } from "../api/domains";
import { EmptyState, ErrorAlert, Spinner } from "../components/ui";

export default function AnalyticsPage() {
  const [days, setDays] = useState(30);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    setError("");
    analyticsApi
      .summary({ days, limit: 10 })
      .then(setSummary)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [days]);

  return (
    <div>
      <div className="page-header">
        <h1>Analytics</h1>
      </div>
      <ErrorAlert message={error} />

      <div className="filter-row">
        <label className="muted" style={{ fontSize: "0.85rem" }}>
          Period:
        </label>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {loading ? (
        <Spinner />
      ) : summary ? (
        <>
          <div className="grid" style={{ marginBottom: 20 }}>
            <div className="stat">
              <div className="label">Changes in period</div>
              <div className="value">{summary.total_changes_in_period}</div>
            </div>
            <div className="stat">
              <div className="label">Avg. changes / day</div>
              <div className="value">{summary.average_daily_changes}</div>
            </div>
            <div className="stat">
              <div className="label">Total potential profit</div>
              <div className="value">{summary.profit_impact.total_potential_profit}</div>
            </div>
            <div className="stat">
              <div className="label">Avg. margin</div>
              <div className="value">{summary.profit_impact.average_margin ?? "—"}</div>
            </div>
          </div>

          <div className="card">
            <h2>Most active suppliers</h2>
            {summary.most_active_suppliers.length === 0 ? (
              <EmptyState>No changes in this period.</EmptyState>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Supplier</th>
                      <th>Changes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.most_active_suppliers.map((s) => (
                      <tr key={s.supplier_id}>
                        <td>{s.supplier_name}</td>
                        <td>{s.change_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="card">
            <h2>Most volatile products</h2>
            {summary.most_volatile_products.length === 0 ? (
              <EmptyState>No changes in this period.</EmptyState>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>Changes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.most_volatile_products.map((p) => (
                      <tr key={p.product_id}>
                        <td>{p.product_name}</td>
                        <td>{p.change_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="grid">
            <div className="card">
              <h2>Largest price increases</h2>
              {summary.largest_price_increases.length === 0 ? (
                <EmptyState>None in this period.</EmptyState>
              ) : (
                <div className="table-wrap">
                  <table>
                    <tbody>
                      {summary.largest_price_increases.map((row, i) => (
                        <tr key={i}>
                          <td>{row.product_name}</td>
                          <td style={{ color: "var(--danger)" }}>+{row.diff}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
            <div className="card">
              <h2>Largest price decreases</h2>
              {summary.largest_price_decreases.length === 0 ? (
                <EmptyState>None in this period.</EmptyState>
              ) : (
                <div className="table-wrap">
                  <table>
                    <tbody>
                      {summary.largest_price_decreases.map((row, i) => (
                        <tr key={i}>
                          <td>{row.product_name}</td>
                          <td style={{ color: "var(--success)" }}>{row.diff}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
