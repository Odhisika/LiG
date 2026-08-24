export function Spinner() {
  return <div className="spinner-wrap">Loading…</div>;
}

export function ErrorAlert({ message }) {
  if (!message) return null;
  return <div className="alert alert-error">{message}</div>;
}

export function SuccessAlert({ message }) {
  if (!message) return null;
  return <div className="alert alert-success">{message}</div>;
}

export function Badge({ value }) {
  if (value === null || value === undefined || value === "") return <span className="muted">—</span>;
  const key = String(value).toLowerCase();
  return <span className={`badge badge-${key}`}>{String(value).replace(/_/g, " ")}</span>;
}

export function EmptyState({ children }) {
  return <div className="empty-state">{children}</div>;
}

export function Modal({ title, onClose, children }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{title}</h2>
        {children}
      </div>
    </div>
  );
}
