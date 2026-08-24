import { useEffect, useState } from "react";
import { discoveryApi } from "../api/domains";
import { EmptyState, ErrorAlert, Modal, Spinner, SuccessAlert } from "../components/ui";

function ImportForm({ discovery, onImport, onCancel, error }) {
  const [price, setPrice] = useState(discovery.price ?? "");
  const [name, setName] = useState(discovery.title || "");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    try {
      const overrides = {};
      if (name && name !== discovery.title) overrides.name = name;
      if (price !== "" && String(price) !== String(discovery.price ?? "")) {
        overrides.supplier_price = price;
      }
      await onImport(overrides);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <ErrorAlert message={error} />
      {discovery.image && (
        <img
          src={discovery.image}
          alt=""
          style={{ width: "100%", maxHeight: 160, objectFit: "contain", marginBottom: 12 }}
        />
      )}
      <div className="form-row">
        <label>Name</label>
        <input value={name} onChange={(e) => setName(e.target.value)} required />
      </div>
      <div className="form-row">
        <label>Supplier price {discovery.price === null && "(not found automatically — required)"}</label>
        <input
          type="number"
          step="0.01"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          required={discovery.price === null}
        />
      </div>
      <p className="muted" style={{ fontSize: "0.8rem" }}>
        {discovery.url}
      </p>
      <div className="modal-actions">
        <button type="button" className="btn" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? "Importing…" : "Import as product"}
        </button>
      </div>
    </form>
  );
}

export default function DiscoveriesPage() {
  const [discoveries, setDiscoveries] = useState([]);
  const [status, setStatus] = useState("pending");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [importing, setImporting] = useState(null);
  const [importError, setImportError] = useState("");
  const [dismissingId, setDismissingId] = useState(null);

  function load() {
    setLoading(true);
    discoveryApi
      .list(status ? { status } : {})
      .then(setDiscoveries)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [status]);

  async function handleImport(overrides) {
    setImportError("");
    try {
      await discoveryApi.import(importing.id, overrides);
      setImporting(null);
      setSuccess(`"${importing.title || importing.url}" imported as a tracked product.`);
      load();
    } catch (err) {
      setImportError(err.message);
    }
  }

  async function handleDismiss(id) {
    setDismissingId(id);
    try {
      await discoveryApi.dismiss(id);
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setDismissingId(null);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Discoveries</h1>
      </div>
      <ErrorAlert message={error} />
      <SuccessAlert message={success} />

      <div className="filter-row">
        <label className="muted" style={{ fontSize: "0.85rem" }}>
          Status:
        </label>
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="pending">Pending review</option>
          <option value="imported">Imported</option>
          <option value="dismissed">Dismissed</option>
          <option value="">All</option>
        </select>
      </div>

      {loading ? (
        <Spinner />
      ) : discoveries.length === 0 ? (
        <EmptyState>
          Nothing here yet — new products found on a supplier's catalog page show up for review.
          Scans run automatically once a day.
        </EmptyState>
      ) : (
        <div className="grid">
          {discoveries.map((d) => (
            <div className="card" key={d.id}>
              {d.image && (
                <img
                  src={d.image}
                  alt=""
                  style={{ width: "100%", height: 120, objectFit: "contain", marginBottom: 10 }}
                />
              )}
              <h2 style={{ fontSize: "0.95rem" }}>{d.title || "(no title captured)"}</h2>
              <p className="muted" style={{ fontSize: "0.85rem", margin: "4px 0" }}>
                {d.supplier_name}
              </p>
              <p style={{ margin: "4px 0" }}>
                {d.price !== null ? `${d.currency} ${d.price}` : <span className="muted">no price found</span>}
              </p>
              {d.status === "pending" && (
                <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                  <button className="btn btn-sm btn-primary" onClick={() => setImporting(d)}>
                    Import
                  </button>
                  <button
                    className="btn btn-sm"
                    disabled={dismissingId === d.id}
                    onClick={() => handleDismiss(d.id)}
                  >
                    Dismiss
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {importing && (
        <Modal title="Import product" onClose={() => setImporting(null)}>
          <ImportForm
            discovery={importing}
            onImport={handleImport}
            onCancel={() => setImporting(null)}
            error={importError}
          />
        </Modal>
      )}
    </div>
  );
}
