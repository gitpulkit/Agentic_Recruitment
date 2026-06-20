export default function CandidateCard({
  row,
  initials,
  checked,
  email,
  disabled,
  onToggle,
  onEmailChange,
  onViewDraft,
}) {
  return (
    <article className={`candidate-card ${checked ? "candidate-card-selected" : ""}`}>
      <div className="candidate-card-top">
        <label className="checkbox-wrap">
          <input
            type="checkbox"
            checked={checked}
            disabled={disabled}
            onChange={onToggle}
          />
          <span className="checkmark" />
        </label>

        <div className="avatar">{initials}</div>

        <div className="candidate-meta">
          <div className="candidate-title">
            <strong>@{row.username}</strong>
            {row.name && <span>{row.name}</span>}
          </div>
          {row.profile_url && (
            <a href={row.profile_url} target="_blank" rel="noreferrer">
              View GitHub profile
            </a>
          )}
        </div>

        <div className="score-badge">{row.score ?? "–"}</div>
      </div>

      <p className="candidate-rationale">{row.rationale}</p>

      <div className="candidate-tags">
        <span className={`tag ${row.qa.passed ? "tag-pass" : "tag-review"}`}>
          {row.qa.passed ? "QA pass" : "Needs review"}
        </span>
        <button type="button" className="text-button" onClick={onViewDraft}>
          Preview draft
        </button>
      </div>

      {checked && (
        <label className="email-field">
          <span>Recipient email</span>
          <input
            type="email"
            placeholder="name@example.com"
            value={email}
            disabled={disabled}
            onChange={(e) => onEmailChange(e.target.value)}
          />
          {!email && row.email && (
            <button
              type="button"
              className="text-button hint-button"
              disabled={disabled}
              onClick={() => onEmailChange(row.email)}
            >
              Use GitHub email ({row.email})
            </button>
          )}
        </label>
      )}
    </article>
  );
}
