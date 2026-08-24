import { useEffect, useState } from "react";
import { pricingApi } from "../api/domains";
import { Badge, EmptyState, ErrorAlert, Modal, Spinner } from "../components/ui";

const STEP_TYPES = [
  { value: "markup_pct", label: "Markup %" },
  { value: "flat_fee", label: "Flat fee" },
  { value: "shipping", label: "Shipping" },
  { value: "tax", label: "Tax %" },
  { value: "fx_convert", label: "FX conversion (multiply)" },
];

function RuleForm({ initial, onSave, onCancel, error }) {
  const [name, setName] = useState(initial?.name || "");
  const [isActive, setIsActive] = useState(initial?.is_active ?? true);
  const [steps, setSteps] = useState(
    initial?.steps_display?.length
      ? initial.steps_display.map((s) => ({ step_type: s.step_type, value: s.value }))
      : [{ step_type: "markup_pct", value: "" }]
  );
  const [saving, setSaving] = useState(false);

  function updateStep(index, field, value) {
    setSteps((s) => s.map((step, i) => (i === index ? { ...step, [field]: value } : step)));
  }

  function addStep() {
    setSteps((s) => [...s, { step_type: "markup_pct", value: "" }]);
  }

  function removeStep(index) {
    setSteps((s) => s.filter((_, i) => i !== index));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave({ name, is_active: isActive, steps });
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <ErrorAlert message={error} />
      <div className="form-row">
        <label>Name</label>
        <input value={name} onChange={(e) => setName(e.target.value)} required />
      </div>

      <div className="form-row">
        <label>Steps (applied in order, top to bottom)</label>
        {steps.map((step, i) => (
          <div key={i} style={{ display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
            <select
              value={step.step_type}
              onChange={(e) => updateStep(i, "step_type", e.target.value)}
              style={{ flex: "1 1 140px" }}
            >
              {STEP_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            <input
              type="number"
              step="0.0001"
              placeholder="value"
              value={step.value}
              onChange={(e) => updateStep(i, "value", e.target.value)}
              style={{ flex: "1 1 80px" }}
              required
            />
            <button
              type="button"
              className="btn btn-sm btn-danger"
              onClick={() => removeStep(i)}
              disabled={steps.length === 1}
            >
              ✕
            </button>
          </div>
        ))}
        <button type="button" className="btn btn-sm" onClick={addStep}>
          + Add step
        </button>
      </div>

      <div className="form-row">
        <label>
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
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

export default function PricingRulesPage() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [editing, setEditing] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  function load() {
    setLoading(true);
    pricingApi
      .list()
      .then(setRules)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleSave(form) {
    setFormError("");
    try {
      if (editing?.id) {
        await pricingApi.update(editing.id, form);
      } else {
        await pricingApi.create(form);
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
      await pricingApi.remove(id);
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
        <h1>Pricing Rules</h1>
        <button className="btn btn-primary" onClick={() => setEditing({})}>
          + New rule
        </button>
      </div>
      <ErrorAlert message={error} />

      {loading ? (
        <Spinner />
      ) : rules.length === 0 ? (
        <EmptyState>
          No pricing rules yet — assign one to a product to auto-update its selling price.
        </EmptyState>
      ) : (
        rules.map((rule) => (
          <div className="card" key={rule.id}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
              <h2 style={{ margin: 0, fontSize: "0.95rem" }}>
                {rule.name} <Badge value={String(rule.is_active)} />
              </h2>
              <div>
                <button className="btn btn-sm" onClick={() => setEditing(rule)}>
                  Edit
                </button>{" "}
                <button
                  className="btn btn-sm btn-danger"
                  disabled={deletingId === rule.id}
                  onClick={() => handleDelete(rule.id)}
                >
                  Delete
                </button>
              </div>
            </div>
            <p className="muted" style={{ fontSize: "0.85rem", marginTop: 10, marginBottom: 0 }}>
              {rule.steps_display.map((s, i) => (
                <span key={i}>
                  {i > 0 && " → "}
                  {STEP_TYPES.find((t) => t.value === s.step_type)?.label || s.step_type}: {s.value}
                </span>
              ))}
            </p>
          </div>
        ))
      )}

      {editing !== null && (
        <Modal title={editing.id ? "Edit pricing rule" : "New pricing rule"} onClose={() => setEditing(null)}>
          <RuleForm initial={editing} onSave={handleSave} onCancel={() => setEditing(null)} error={formError} />
        </Modal>
      )}
    </div>
  );
}
