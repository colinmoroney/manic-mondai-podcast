// Gates everything under /sample/ (the page, the PDF and the audio) behind a signed link.
//
// The email sent by netlify/functions/submission-created.mjs carries ?k=<submission id>.<HMAC>.
// A valid key on any /sample/* request sets a cookie scoped to /sample, so the page's own links to
// the PDF and audio, and the embedded player, work without the key. Everyone else gets a 403 page
// that points to the request form. Fails closed if SAMPLE_LINK_SECRET is missing.

import type { Config, Context } from "@netlify/edge-functions";

const COOKIE = "manic_sample";
const COOKIE_DAYS = 30;

async function hmacHex(secret: string, message: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(message));
  return Array.from(new Uint8Array(sig)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

function equal(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

async function validKey(secret: string, key: string | null | undefined): Promise<boolean> {
  if (!key) return false;
  const dot = key.lastIndexOf(".");
  if (dot <= 0) return false;
  const id = key.slice(0, dot);
  const sig = key.slice(dot + 1);
  if (!/^[A-Za-z0-9_-]{1,64}$/.test(id) || !/^[0-9a-f]{64}$/.test(sig)) return false;
  return equal(await hmacHex(secret, id), sig);
}

const DENIED = `<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>Manic AI for RevOps: sample issue</title>
<style>
  body{margin:0;background:#fffcf5;color:#16130f;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.5}
  main{max-width:34rem;margin:0 auto;padding:4rem 1.25rem}
  h1{font-size:1.75rem;line-height:1.15;letter-spacing:-0.02em;margin:0 0 1rem}
  p{margin:0 0 1rem;color:#3c362e}
  a.btn{display:inline-block;background:#ff3d00;color:#fff;text-decoration:none;font-weight:700;padding:0.8rem 1.3rem;border-radius:999px}
  .brand{font-weight:800;text-transform:uppercase;letter-spacing:-0.01em;margin-bottom:2rem}
  .brand span{color:#ff3d00}
</style></head>
<body><main>
<div class="brand">Manic<span>*</span>AI</div>
<h1>The sample issue is sent by email.</h1>
<p>This page opens from the link in that email. If you have the email, click the link in it again. If you have not asked for a sample yet, it takes thirty seconds.</p>
<p><a class="btn" href="/#pricing">Get a sample issue</a></p>
</main></body></html>`;

export default async (request: Request, context: Context) => {
  const secret = Netlify.env.get("SAMPLE_LINK_SECRET");
  if (!secret) {
    console.error("sample-gate: SAMPLE_LINK_SECRET is not set; refusing to serve /sample");
    return new Response("Sample issue temporarily unavailable.", { status: 503, headers: { "cache-control": "no-store" } });
  }

  const url = new URL(request.url);
  const fromLink = url.searchParams.get("k");

  if (await validKey(secret, fromLink)) {
    const response = await context.next();
    const out = new Response(response.body, response);
    out.headers.append(
      "Set-Cookie",
      `${COOKIE}=${fromLink}; Path=/sample; Max-Age=${COOKIE_DAYS * 86400}; Secure; HttpOnly; SameSite=Lax`,
    );
    out.headers.set("cache-control", "private, no-store");
    return out;
  }

  if (await validKey(secret, context.cookies.get(COOKIE))) {
    const response = await context.next();
    const out = new Response(response.body, response);
    out.headers.set("cache-control", "private, no-store");
    return out;
  }

  return new Response(DENIED, {
    status: 403,
    headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" },
  });
};

export const config: Config = {
  path: ["/sample", "/sample/*"],
  onError: "fail",
};
