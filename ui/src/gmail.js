const GMAIL_COMPOSE_BASE = "https://mail.google.com/mail/?view=cm&fs=1";

/** Gmail compose URLs have a practical length limit in browsers. */
const MAX_COMPOSE_URL_LENGTH = 7500;

export function buildGmailComposeUrl({ to, subject, body }) {
  const params = new URLSearchParams();
  if (to) params.set("to", to);
  if (subject) params.set("su", subject);
  if (body) params.set("body", body);

  return `${GMAIL_COMPOSE_BASE}&${params.toString()}`;
}

export function getComposeUrlMeta({ to, subject, body }) {
  const url = buildGmailComposeUrl({ to, subject, body });
  return {
    url,
    tooLong: url.length > MAX_COMPOSE_URL_LENGTH,
    length: url.length,
  };
}

export function openGmailCompose(draft) {
  const meta = getComposeUrlMeta({
    to: draft.to,
    subject: draft.subject || "",
    body: draft.body || "",
  });

  if (meta.tooLong) {
    throw new Error(
      "This draft is too long for a Gmail compose link. Shorten the email body or send via SMTP."
    );
  }

  window.open(meta.url, "_blank", "noopener,noreferrer");
}
