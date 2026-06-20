export default function DraftModal({ row, onClose }) {
  if (!row) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <p className="modal-kicker">Outreach draft</p>
            <h3>@{row.username}</h3>
          </div>
          <button type="button" className="text-button" onClick={onClose}>
            Close
          </button>
        </div>

        <div className="modal-subject">
          <span>Subject</span>
          <strong>{row.draft.subject}</strong>
        </div>

        <pre className="modal-body">{row.draft.body}</pre>

        {row.qa.issues?.length > 0 && (
          <div className="modal-issues">
            <strong>QA notes</strong>
            <ul>
              {row.qa.issues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
