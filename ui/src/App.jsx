import { useEffect, useMemo, useState } from "react";
import {
  createCampaign,
  getCampaign,
  getEmailSettings,
  pollCampaign,
  saveSelection,
  sendEmails,
} from "./api.js";
import CandidateCard from "./CandidateCard.jsx";
import DraftModal from "./DraftModal.jsx";
import { openGmailCompose } from "./gmail.js";

const STATUS_LABELS = {
  running: "Running pipeline",
  ready: "Ready for review",
  confirmed: "Selection saved",
  sent: "Emails sent",
  failed: "Failed",
};

function initials(name, username) {
  const source = name || username || "?";
  return source
    .split(/\s+/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export default function App() {
  const [file, setFile] = useState(null);
  const [topK, setTopK] = useState(5);
  const [outreachN, setOutreachN] = useState(3);
  const [campaign, setCampaign] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [emails, setEmails] = useState({});
  const [draftRow, setDraftRow] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [emailSettings, setEmailSettings] = useState({ configured: false });
  const [sendResults, setSendResults] = useState(null);

  useEffect(() => {
    getEmailSettings()
      .then(setEmailSettings)
      .catch(() => setEmailSettings({ configured: false }));
  }, []);

  useEffect(() => {
    if (!campaign?.id || campaign.status !== "running") return undefined;
    return pollCampaign(campaign.id, (updated, pollError) => {
      if (pollError) {
        setError(pollError);
        return;
      }
      setCampaign(updated);
      if (updated.status === "ready") {
        const defaults = new Set(
          updated.rows.filter((row) => row.qa.passed).map((row) => row.username)
        );
        setSelected(defaults);
        const nextEmails = {};
        updated.rows.forEach((row) => {
          nextEmails[row.username] = row.email || "";
        });
        setEmails(nextEmails);
      }
    });
  }, [campaign?.id, campaign?.status]);

  useEffect(() => {
    if (campaign?.send_results) {
      setSendResults(campaign.send_results);
    }
  }, [campaign?.send_results]);

  const selectedCount = selected.size;
  const statusLabel = useMemo(() => {
    if (!campaign) return "";
    return STATUS_LABELS[campaign.status] || campaign.status;
  }, [campaign]);

  const selectedWithEmail = Array.from(selected).filter((username) =>
    (emails[username] || "").trim()
  ).length;

  const gmailDrafts = useMemo(() => {
    if (!campaign?.rows) return [];
    return campaign.rows
      .filter((row) => selected.has(row.username))
      .map((row) => ({
        username: row.username,
        to: (emails[row.username] || "").trim(),
        subject: row.draft?.subject || "",
        body: row.draft?.body || "",
      }));
  }, [campaign?.rows, selected, emails]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSendResults(null);
    if (!file) {
      setError("Choose a job description file first.");
      return;
    }

    setBusy(true);
    try {
      const created = await createCampaign(file, topK, outreachN);
      setCampaign({ ...created, rows: [], email_configured: emailSettings.configured });
      setSelected(new Set());
      setEmails({});
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function toggleUsername(username) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(username)) next.delete(username);
      else next.add(username);
      return next;
    });
  }

  function updateEmail(username, value) {
    setEmails((prev) => ({ ...prev, [username]: value }));
  }

  function buildEmailPayload() {
    const payload = {};
    selected.forEach((username) => {
      payload[username] = (emails[username] || "").trim();
    });
    return payload;
  }

  async function handleConfirm() {
    if (!campaign?.id) return;
    setBusy(true);
    setError("");
    try {
      const updated = await saveSelection(
        campaign.id,
        Array.from(selected),
        buildEmailPayload()
      );
      setCampaign(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function handleOpenGmail(draft) {
    setError("");
    try {
      openGmailCompose(draft);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleSendSmtp() {
    if (!campaign?.id) return;
    setBusy(true);
    setError("");
    try {
      await saveSelection(campaign.id, Array.from(selected), buildEmailPayload());
      const result = await sendEmails(campaign.id);
      setSendResults(result.results);
      const updated = await getCampaign(campaign.id);
      setCampaign(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const isLocked = campaign?.status === "sent";
  const showSendStep = gmailDrafts.length > 0;

  return (
    <div className="app-shell">
      <div className="ambient ambient-a" />
      <div className="ambient ambient-b" />

      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">AR</div>
          <div>
            <h1>Agentic Recruiter</h1>
            <p>Source candidates, review drafts, send outreach.</p>
          </div>
        </div>
        {campaign && (
          <span className={`status-pill status-${campaign.status}`}>
            {statusLabel}
          </span>
        )}
      </header>

      <section className="panel upload-panel">
        <div className="panel-heading">
          <span className="step-badge">1</span>
          <div>
            <h2>New campaign</h2>
            <p>Upload a job description to start sourcing on GitHub.</p>
          </div>
        </div>

        <form className="upload-form" onSubmit={handleSubmit}>
          <label className="dropzone">
            <input
              type="file"
              accept=".txt,text/plain"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            <strong>{file ? file.name : "Drop a .txt JD or click to browse"}</strong>
            <span>We research candidates, draft emails, and QA each draft.</span>
          </label>

          <div className="controls-row">
            <label>
              <span>Candidates to research</span>
              <input
                type="number"
                min="1"
                max="10"
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
              />
            </label>
            <label>
              <span>Drafts to generate</span>
              <input
                type="number"
                min="1"
                max="10"
                value={outreachN}
                onChange={(e) => setOutreachN(Number(e.target.value))}
              />
            </label>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={busy || campaign?.status === "running"}
            >
              {campaign?.status === "running" ? "Running pipeline…" : "Start campaign"}
            </button>
          </div>
        </form>
      </section>

      {campaign?.status === "running" && (
        <section className="panel loading-panel">
          <div className="loader" />
          <div>
            <h3>Sourcing and drafting outreach</h3>
            <p>This usually takes a few minutes. GitHub + OpenAI calls are running.</p>
          </div>
        </section>
      )}

      {error && <div className="alert alert-error">{error}</div>}

      {campaign?.status === "failed" && (
        <div className="alert alert-error">
          {campaign.error || "Campaign failed. Check your API keys and try again."}
        </div>
      )}

      {campaign?.rows?.length > 0 && (
        <section className="panel review-panel">
          <div className="panel-heading">
            <span className="step-badge">2</span>
            <div>
              <h2>Review candidates</h2>
              <p>Select who should receive outreach and add their email address.</p>
            </div>
          </div>

          <div className="candidate-grid">
            {campaign.rows.map((row) => (
              <CandidateCard
                key={row.username}
                row={row}
                initials={initials(row.name, row.username)}
                checked={selected.has(row.username)}
                email={emails[row.username] || ""}
                disabled={isLocked}
                onToggle={() => toggleUsername(row.username)}
                onEmailChange={(value) => updateEmail(row.username, value)}
                onViewDraft={() => setDraftRow(row)}
              />
            ))}
          </div>

          {!isLocked && (
            <div className="action-bar">
              <div className="action-meta">
                <strong>{selectedCount}</strong> selected ·{" "}
                <strong>{selectedWithEmail}</strong> with email
              </div>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={busy || selectedCount === 0}
                onClick={handleConfirm}
              >
                Save selection
              </button>
            </div>
          )}
        </section>
      )}

      {showSendStep && (
        <section className="panel send-panel">
          <div className="panel-heading">
            <span className="step-badge">3</span>
            <div>
              <h2>Send via Gmail</h2>
              <p>
                Opens Gmail in a new tab with the draft pre-filled. Sign in if
                prompted, review the message, then press Send in Gmail.
              </p>
            </div>
          </div>

          <div className="gmail-list">
            {gmailDrafts.map((draft) => (
              <div key={draft.username} className="gmail-row">
                <div>
                  <strong>@{draft.username}</strong>
                  <span className="muted">
                    {draft.to || "Add recipient email above"}
                  </span>
                  <span className="muted gmail-subject">{draft.subject}</span>
                </div>
                <button
                  type="button"
                  className="btn btn-gmail"
                  disabled={!draft.to}
                  onClick={() => handleOpenGmail(draft)}
                >
                  Open in Gmail
                </button>
              </div>
            ))}
          </div>

          {emailSettings.configured && (
            <div className="smtp-block">
              <div className="smtp-heading">
                <h3>Or send automatically</h3>
                <p>Uses SMTP from your <code>.env</code> without opening Gmail.</p>
              </div>
              <div className="action-bar smtp-action">
                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={
                    busy || selectedWithEmail === 0 || isLocked || !emailSettings.configured
                  }
                  onClick={handleSendSmtp}
                >
                  {isLocked
                    ? "Emails sent via SMTP"
                    : `Send ${selectedWithEmail} via SMTP`}
                </button>
              </div>
              {sendResults && (
                <div className="send-results">
                  {sendResults.map((item) => (
                    <div
                      key={item.username}
                      className={`send-result send-${item.status}`}
                    >
                      <strong>@{item.username}</strong>
                      <span>{item.detail}</span>
                      {item.email && <span className="muted">{item.email}</span>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      )}

      <DraftModal row={draftRow} onClose={() => setDraftRow(null)} />
    </div>
  );
}
