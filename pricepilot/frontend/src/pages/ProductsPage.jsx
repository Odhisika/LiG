import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { productsApi } from "../api/products";
import { suppliersApi } from "../api/suppliers";
import { pricingApi } from "../api/domains";
import { Badge, EmptyState, ErrorAlert, Modal, Spinner } from "../components/ui";

const STATUSES = ["active", "paused", "out_of_stock", "scrape_failed", "archived"];
const CURRENCIES = ["USD", "EUR", "GBP", "CNY", "GHS", "NGN", "OTHER"];

function emptyForm(suppliers) {
  return {
    supplier: suppliers[0]?.id || "",
    name: "",
    supplier_url: "",
    sku: "",
    supplier_price: "",
    selling_price: "",
    pricing_rule: "",
    currency: "USD",
    status: "active",
    stock: "",
    category: "",
    check_frequency_minutes: 60,
  };
}

function ProductForm({ initial, suppliers, pricingRules, onSave, onCancel, error }) {
  const [form, setForm] = useState(initial);
  const [saving, setSaving] = useState(false);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        ...form,
        selling_price: form.selling_price === "" ? null : form.selling_price,
        stock: form.stock === "" ? null : Number(form.stock),
        pricing_rule: form.pricing_rule || null,
      };
      await onSave(payload);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <ErrorAlert message={error} />
      <div className="form-row">
        <label>Supplier</label>
        <select value={form.supplier} onChange={(e) => update("supplier", e.target.value)} required>
          {suppliers.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </div>
      <div className="form-row">
        <label>Name</label>
        <input value={form.name} onChange={(e) => update("name", e.target.value)} required />
      </div>
      <div className="form-row">
        <label>Supplier product URL</label>
        <input
          type="url"
          value={form.supplier_url}
          onChange={(e) => update("supplier_url", e.target.value)}
          required
        />
      </div>
      <div className="form-grid">
        <div className="form-row">
          <label>SKU</label>
          <input value={form.sku} onChange={(e) => update("sku", e.target.value)} />
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
          <label>Supplier price</label>
          <input
            type="number"
            step="0.01"
            value={form.supplier_price}
            onChange={(e) => update("supplier_price", e.target.value)}
            required
          />
        </div>
        <div className="form-row">
          <label>Selling price (optional)</label>
          <input
            type="number"
            step="0.01"
            value={form.selling_price}
            onChange={(e) => update("selling_price", e.target.value)}
          />
        </div>
      </div>
      <div className="form-row">
        <label>Pricing rule (auto-updates selling price)</label>
        <select value={form.pricing_rule || ""} onChange={(e) => update("pricing_rule", e.target.value)}>
          <option value="">None — manual pricing</option>
          {pricingRules.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
      </div>
      <div className="form-grid">
        <div className="form-row">
          <label>Status</label>
          <select value={form.status} onChange={(e) => update("status", e.target.value)}>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div className="form-row">
          <label>Stock</label>
          <input type="number" value={form.stock} onChange={(e) => update("stock", e.target.value)} />
        </div>
      </div>
      <div className="form-grid">
        <div className="form-row">
          <label>Category</label>
          <input value={form.category} onChange={(e) => update("category", e.target.value)} />
        </div>
        <div className="form-row">
          <label>Check frequency (minutes)</label>
          <input
            type="number"
            min={1}
            value={form.check_frequency_minutes}
            onChange={(e) => update("check_frequency_minutes", Number(e.target.value))}
          />
        </div>
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

export default function ProductsPage() {
  const [products, setProducts] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [pricingRules, setPricingRules] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [editing, setEditing] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [searchParams, setSearchParams] = useSearchParams();
  const categoryFilter = searchParams.get("category") || "";

  function load() {
    setLoading(true);
    Promise.all([
      productsApi.list(
        Object.fromEntries(
          Object.entries({
            status: statusFilter,
            category: categoryFilter,
          }).filter(([, v]) => v)
        )
      ),
      suppliersApi.list(),
      pricingApi.list(),
      productsApi.categories(),
    ])
      .then(([p, s, r, c]) => {
        setProducts(p);
        setSuppliers(s);
        setPricingRules(r);
        setCategories(c);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [statusFilter, categoryFilter]);

  function setCategoryFilter(value) {
    if (value) {
      setSearchParams(value ? { category: value } : {});
    } else {
      setSearchParams({});
    }
  }

  async function handleSave(form) {
    setFormError("");
    try {
      if (editing?.id) {
        await productsApi.update(editing.id, form);
      } else {
        await productsApi.create(form);
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
      await productsApi.remove(id);
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setDeletingId(null);
    }
  }

  function openEdit(product) {
    setEditing({
      ...product,
      supplier: product.supplier,
      pricing_rule: product.pricing_rule || "",
      selling_price: product.selling_price ?? "",
      stock: product.stock ?? "",
    });
  }

  return (
    <div>
      <div className="page-header">
        <h1>Products</h1>
        <button
          className="btn btn-primary"
          disabled={suppliers.length === 0}
          onClick={() => setEditing(emptyForm(suppliers))}
          title={suppliers.length === 0 ? "Add a supplier first" : ""}
        >
          + New product
        </button>
      </div>
      <ErrorAlert message={error} />

      <div className="filter-row">
        <label className="muted" style={{ fontSize: "0.85rem" }}>
          Status:
        </label>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <label className="muted" style={{ fontSize: "0.85rem" }}>
          Category:
        </label>
        <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
          <option value="">All</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <Spinner />
      ) : products.length === 0 ? (
        <EmptyState>
          {suppliers.length === 0
            ? "Add a supplier first, then add products to track."
            : "No products match this filter."}
        </EmptyState>
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Supplier</th>
                <th>Supplier price</th>
                <th>Selling price</th>
                <th>Stock</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr key={p.id}>
                  <td>{p.name}</td>
                  <td>{p.supplier_name}</td>
                  <td>
                    {p.currency} {p.supplier_price}
                  </td>
                  <td>{p.effective_selling_price !== null ? `${p.currency} ${p.effective_selling_price}` : "—"}</td>
                  <td>{p.stock ?? "—"}</td>
                  <td>
                    <Badge value={p.status} />
                  </td>
                  <td>
                    <button className="btn btn-sm" onClick={() => openEdit(p)}>
                      Edit
                    </button>{" "}
                    <button
                      className="btn btn-sm btn-danger"
                      disabled={deletingId === p.id}
                      onClick={() => handleDelete(p.id)}
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
        <Modal title={editing.id ? "Edit product" : "New product"} onClose={() => setEditing(null)}>
          <ProductForm
            initial={editing}
            suppliers={suppliers}
            pricingRules={pricingRules}
            onSave={handleSave}
            onCancel={() => setEditing(null)}
            error={formError}
          />
        </Modal>
      )}
    </div>
  );
}
