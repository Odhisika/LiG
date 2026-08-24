import { useEffect, useState } from "react";
import { historyApi } from "../api/domains";
import { productsApi } from "../api/products";
import { EmptyState, ErrorAlert, Spinner } from "../components/ui";

export default function HistoryPage() {
  const [entries, setEntries] = useState([]);
  const [products, setProducts] = useState([]);
  const [productFilter, setProductFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    productsApi.list().then(setProducts).catch(() => {});
  }, []);

  function load() {
    setLoading(true);
    historyApi
      .list(productFilter ? { product: productFilter } : {})
      .then(setEntries)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [productFilter]);

  return (
    <div>
      <div className="page-header">
        <h1>History</h1>
      </div>
      <ErrorAlert message={error} />

      <div className="filter-row">
        <label className="muted" style={{ fontSize: "0.85rem" }}>
          Product:
        </label>
        <select value={productFilter} onChange={(e) => setProductFilter(e.target.value)}>
          <option value="">All products</option>
          {products.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <Spinner />
      ) : entries.length === 0 ? (
        <EmptyState>No price changes recorded yet — this fills in once the scheduler runs.</EmptyState>
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Price</th>
                  <th>Stock</th>
                  <th>Source</th>
                  <th>When</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e) => (
                  <tr key={e.id}>
                    <td>{e.product_name}</td>
                    <td>
                      {e.price_changed ? (
                        <>
                          {e.old_price} → {e.new_price}{" "}
                          <span className={e.price_diff >= 0 ? "muted" : "muted"}>
                            ({e.price_diff >= 0 ? "+" : ""}
                            {e.price_diff})
                          </span>
                        </>
                      ) : (
                        <span className="muted">unchanged</span>
                      )}
                    </td>
                    <td>
                      {e.stock_changed ? (
                        <>
                          {e.old_stock ?? "—"} → {e.new_stock ?? "—"}
                        </>
                      ) : (
                        <span className="muted">unchanged</span>
                      )}
                    </td>
                    <td>{e.source || "—"}</td>
                    <td className="muted">{new Date(e.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
