const API_BASE = "/api";

export async function getEmailSettings() {
  const resp = await fetch(`${API_BASE}/settings/email`);
  if (!resp.ok) throw new Error("Failed to load email settings");
  return resp.json();
}

export async function createCampaign(file, topK, outreachN) {
  const form = new FormData();
  form.append("jd_file", file);
  form.append("top_k", String(topK));
  form.append("outreach_n", String(outreachN));

  const resp = await fetch(`${API_BASE}/campaigns`, {
    method: "POST",
    body: form,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to start campaign");
  }
  return resp.json();
}

export async function getCampaign(campaignId) {
  const resp = await fetch(`${API_BASE}/campaigns/${campaignId}`);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to load campaign");
  }
  return resp.json();
}

export async function saveSelection(campaignId, usernames, emails) {
  const resp = await fetch(`${API_BASE}/campaigns/${campaignId}/selection`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ usernames, emails }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to save selection");
  }
  return resp.json();
}

export async function sendEmails(campaignId) {
  const resp = await fetch(`${API_BASE}/campaigns/${campaignId}/send`, {
    method: "POST",
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to send emails");
  }
  return resp.json();
}

export function pollCampaign(campaignId, onUpdate, intervalMs = 2500) {
  let stopped = false;

  const tick = async () => {
    if (stopped) return;
    try {
      const campaign = await getCampaign(campaignId);
      onUpdate(campaign);
      if (campaign.status === "ready" || campaign.status === "failed") {
        stopped = true;
        return;
      }
    } catch (err) {
      onUpdate(null, err.message);
      stopped = true;
      return;
    }
    setTimeout(tick, intervalMs);
  };

  tick();
  return () => {
    stopped = true;
  };
}
