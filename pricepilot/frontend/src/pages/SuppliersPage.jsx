import { useEffect, useState } from "react";
import { suppliersApi } from "../api/suppliers";
import { Badge, EmptyState, ErrorAlert, Modal, Spinner } from "../components/ui";

const CURRENCIES = ["USD", "EUR", "GBP", "CNY", "GHS", "NGN", "OTHER"];

const EMPTY_FORM = {
  name: "",
  website: "",
  catalog_url: "",
  country: "",
  currency: "USD",
  default_scraper: "",
  rate_limit_per_minute: 10,
  is_active: true,
};

function SupplierForm({ initial, onSave, onCancel, error }) {
  const [form, setForm] = useState(initial || EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave(form);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <ErrorAlert message={error} />
      <div className="form-row">
        <label>Name</label>
        <input value={form.name} onChange={(e) => update("name", e.target.value)} required />
      </div>
      <div className="form-row">
        <label>Website</label>
        <input
          type="url"
          value={form.website}
          onChange={(e) => update("website", e.target.value)}
          required
        />
      </div>
      <div className="form-row">
        <label>Catalog URL (optional — defaults to website)</label>
        <input
          type="url"
          value={form.catalog_url}
          onChange={(e) => update("catalog_url", e.target.value)}
        />
      </div>
      <div className="form-grid">
        <div className="form-row">
          <label>Country</label>
          <input value={form.country} onChange={(e) => update("country", e.target.value)} />
        </div>
        <div className="form-row">
          <label>Currency</label>
          <select value={form.currency} onChange={(e) => update("currency", e.target.value)}>
            {CURRENCIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="form-grid">
        <div className="form-row">
          <label>Scraper</label>
          <select
            value={form.default_scraper}
            onChange={(e) => update("default_scraper", e.target.value)}
          >
            <option value="">None</option>
            <option value="catlog">catlog</option>
          </select>
        </div>
        <div className="form-row">
          <label>Rate limit / min</label>
          <input
            type="number"
            min={1}
            value={form.rate_limit_per_minute}
            onChange={(e) => update("rate_limit_per_minute", Number(e.target.value))}
          />
        </div>
      </div>
      <div className="form-row">
        <label>
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(e) => update("is_active", e.target.checked)}
            style={{ marginRight: 6 }}
          />
          Active
        </label>
      </div>
      <div className="modal-actions">
        <button type="button" className="btn" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
    </form>
  );
}

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [editing, setEditing] = useState(null); // null = closed, {} = new, {...} = editing
  const [deletingId, setDeletingId] = useState(null);

  function load() {
    setLoading(true);
    suppliersApi
      .list()
      .then(setSuppliers)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleSave(form) {
    setFormError("");
    try {
      if (editing?.id) {
        await suppliersApi.update(editing.id, form);
      } else {
        await suppliersApi.create(form);
      }
      setEditing(null);
      load();
    } catch (err) {
      setFormError(err.message);
    }
  }

  async function handleDelete(id) {
    setDeletingId(id);
    try {
      await suppliersApi.remove(id);
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Suppliers</h1>
        <button className="btn btn-primary" onClick={() => setEditing({})}>
          + New supplier
        </button>
      </div>
      <ErrorAlert message={error} />

      {loading ? (
        <Spinner />
      ) : suppliers.length === 0 ? (
        <EmptyState>No suppliers yet — add one to start tracking products.</EmptyState>
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Website</th>
                <th>Currency</th>
                <th>Scraper</th>
                <th>Active</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map((s) => (
                <tr key={s.id}>
                  <td>{s.name}</td>
                  <td>
                    <a href={s.website} target="_blank" rel="noreferrer">
                      {s.website.replace(/^https?:\/\//, "")}
                    </a>
                  </td>
                  <td>{s.currency}</td>
                  <td>{s.default_scraper || <span className="muted">none</span>}</td>
                  <td>
                    <Badge value={String(s.is_active)} />
                  </td>
                  <td>
                    <button className="btn btn-sm" onClick={() => setEditing(s)}>
                      Edit
                    </button>{" "}
                    <button
                      className="btn btn-sm btn-danger"
                      disabled={deletingId === s.id}
                      onClick={() => handleDelete(s.id)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}

      {editing !== null && (
        <Modal title={editing.id ? "Edit supplier" : "New supplier"} onClose={() => setEditing(null)}>
          <SupplierForm
            initial={editing.id ? editing : EMPTY_FORM}
            onSave={handleSave}
            onCancel={() => setEditing(null)}
            error={formError}
          />
        </Modal>
      )}
    </div>
  );
}
