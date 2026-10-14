// Sends the sample issue to anyone who submits the "founding-teams" form on thisismanic.ai.
//
// Netlify runs a function with this file name on every verified form submission (spam-flagged
// submissions never reach it). The email goes out through Resend from info@thisismanic.ai.
//
// Every link in the email carries ?k=<submission id>.<HMAC-SHA256>, and the edge function
// netlify/edge-functions/sample-gate.ts only serves /sample/* to requests that carry a valid key
// (or the cookie it sets). Both sides read the same SAMPLE_LINK_SECRET.
//
// Environment variables (set in the Netlify UI, scope: Functions):
//   RESEND_API_KEY     required, a Resend key with sending access for thisismanic.ai
//   SAMPLE_LINK_SECRET required, the shared secret that signs the sample links
//   SAMPLE_FROM      optional, default "Colin at Manic AI <info@thisismanic.ai>"
//   SAMPLE_REPLY_TO  optional, default "info@thisismanic.ai"
//   SAMPLE_BCC       optional, an address that gets a copy of every email sent
//
// The copy below is mirrored in the private repo at outreach/sample-issue-email.md.

import { createHmac } from "node:crypto";

const SITE = "https://thisismanic.ai";
const PRICING = `${SITE}/#pricing`;

// One signed key per submission; the edge function recomputes the HMAC to check it.
function signedLinks(secret, submissionId) {
  const id = String(submissionId).replace(/[^A-Za-z0-9_-]/g, "").slice(0, 64);
  const sig = createHmac("sha256", secret).update(id).digest("hex");
  const k = encodeURIComponent(`${id}.${sig}`);
  return {
    page: `${SITE}/sample/?k=${k}`,
    pdf: `${SITE}/sample/manic-ai-for-revops-sample-2026-10-12.pdf?k=${k}`,
    audio: `${SITE}/sample/revops-sample-2026-10-12.m4a?k=${k}`,
  };
}

const escapeHtml = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function textBody(first, L) {
  return `Hi ${first},

Thanks for asking. Here is a sample issue of Manic AI for RevOps, the week of 12 October 2026.

Read it here: ${L.page}
PDF: ${L.pdf}
Audio companion (12 minutes): ${L.audio}
The player is also at the bottom of the web version. These links are yours; they open for you without a login.

Four items this week, one action each:

1. Microsoft and Google both shipped an agent that wants to sit in front of your CRM. Sort your CRM write actions into one-way and two-way doors before anyone turns the skills on.
2. Anthropic published what its own model did when nobody told it not to. Write the cage (read-only credentials, allow-listed sites, human sign-off on form submissions) before the first skill is enabled.
3. LinkedIn tripled an agent's accuracy by writing down what its data means. Start a definitions file for pipeline, ARR, churn and attribution before the dashboards arrive.
4. An agent-built exit experiment is now a few days of work. Run one before your next GTM renewal and bring the number to the table.

Every claim in the issue is linked to its source.

If this is useful, the brief is weekly and the plans are at ${PRICING}. Basic is $99 USD per team per month and includes the audio companion. Pro adds a branded digest, custom voices and longer episodes.

Reply to this email if you have a question. I read every one.

Colin
Manic AI
https://thisismanic.ai
`;
}

function htmlBody(first, L) {
  const p = (s) => `<p style="margin:0 0 1em">${s}</p>`;
  const a = (href, label) => `<a href="${href}" style="color:#c22f00">${label || href}</a>`;
  return `<!doctype html><html><body style="margin:0;padding:24px;background:#fffcf5;color:#16130f;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:16px;line-height:1.5">
<div style="max-width:600px;margin:0 auto">
${p(`Hi ${escapeHtml(first)},`)}
${p("Thanks for asking. Here is a sample issue of <strong>Manic AI for RevOps</strong>, the week of 12 October 2026.")}
${p(`Read it here: ${a(L.page, "thisismanic.ai/sample")}<br>PDF: ${a(L.pdf, "manic-ai-for-revops-sample-2026-10-12.pdf")}<br>Audio companion (12 minutes): ${a(L.audio, "revops-sample-2026-10-12.m4a")}<br>The player is also at the bottom of the web version. These links are yours; they open for you without a login.`)}
${p("Four items this week, one action each:")}
<ol style="margin:0 0 1em;padding-left:1.25em">
<li style="margin-bottom:0.5em">Microsoft and Google both shipped an agent that wants to sit in front of your CRM. Sort your CRM write actions into one-way and two-way doors before anyone turns the skills on.</li>
<li style="margin-bottom:0.5em">Anthropic published what its own model did when nobody told it not to. Write the cage (read-only credentials, allow-listed sites, human sign-off on form submissions) before the first skill is enabled.</li>
<li style="margin-bottom:0.5em">LinkedIn tripled an agent's accuracy by writing down what its data means. Start a definitions file for pipeline, ARR, churn and attribution before the dashboards arrive.</li>
<li style="margin-bottom:0.5em">An agent-built exit experiment is now a few days of work. Run one before your next GTM renewal and bring the number to the table.</li>
</ol>
${p("Every claim in the issue is linked to its source.")}
${p(`If this is useful, the brief is weekly and the plans are at ${a(PRICING, "thisismanic.ai/#pricing")}. Basic is $99 USD per team per month and includes the audio companion. Pro adds a branded digest, custom voices and longer episodes.`)}
${p("Reply to this email if you have a question. I read every one.")}
${p("Colin<br>Manic AI<br>" + a("https://thisismanic.ai", "thisismanic.ai"))}
</div></body></html>`;
}

export default async (req) => {
  let payload;
  try {
    ({ payload } = await req.json());
  } catch (err) {
    console.error("submission-created: could not parse event body", err);
    return new Response("bad event", { status: 400 });
  }
  if (!payload || payload.form_name !== "founding-teams") {
    return new Response("ignored", { status: 200 });
  }

  const data = payload.data || {};
  const to = String(data.email || "").trim();
  if (!to) {
    console.warn("submission-created: submission had no email", payload.id);
    return new Response("no email", { status: 200 });
  }
  const first = String(data.name || "").trim().split(/\s+/)[0] || "there";

  const key = Netlify.env.get("RESEND_API_KEY");
  if (!key) {
    console.error("submission-created: RESEND_API_KEY is not set; no email sent for", payload.id);
    return new Response("not configured", { status: 500 });
  }
  const linkSecret = Netlify.env.get("SAMPLE_LINK_SECRET");
  if (!linkSecret) {
    console.error("submission-created: SAMPLE_LINK_SECRET is not set; no email sent for", payload.id);
    return new Response("not configured", { status: 500 });
  }
  const links = signedLinks(linkSecret, payload.id);
  const from = Netlify.env.get("SAMPLE_FROM") || "Colin at Manic AI <info@thisismanic.ai>";
  const replyTo = Netlify.env.get("SAMPLE_REPLY_TO") || "info@thisismanic.ai";
  const bcc = Netlify.env.get("SAMPLE_BCC");

  const body = {
    from,
    to: [to],
    reply_to: replyTo,
    subject: "Your Manic AI for RevOps sample issue",
    text: textBody(first, links),
    html: htmlBody(first, links),
    headers: { "X-Entity-Ref-ID": String(payload.id || "") },
  };
  if (bcc) body.bcc = [bcc];

  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    console.error("submission-created: Resend returned", r.status, await r.text());
    return new Response("send failed", { status: 502 });
  }
  const result = await r.json();
  console.log("submission-created: sent sample issue, submission", payload.id, "email", result.id);
  return new Response("sent", { status: 200 });
};
