#!/usr/bin/env node
/**
 * fetch-feedback.js
 * Fetches TestFlight beta feedback via App Store Connect API (JWT auth, no browser needed).
 * Usage: node fetch-feedback.js [--json]
 */

const fs = require('fs');
const https = require('https');
const crypto = require('crypto');

// ── Config ────────────────────────────────────────────────────────────────────
const KEY_ID     = 'SG7TT6R2M5';
const ISSUER_ID  = 'bf80d46b-2de4-42da-ac4a-26b2dca0e122';
const APP_ID     = '6759486622';
const KEY_FILE   = '/Users/deeksharastogi/projects/souschef/ios/fastlane/api_key.p8';
const SEEN_FILE  = '/Users/deeksharastogi/clawd/skills/testflight-feedback/references/seen-feedback.json';

// ── JWT (ES256 — raw r||s encoding required by JWT spec) ─────────────────────
function generateJWT() {
  const privateKey = fs.readFileSync(KEY_FILE, 'utf8');
  const now = Math.floor(Date.now() / 1000);
  const header  = Buffer.from(JSON.stringify({ alg: 'ES256', typ: 'JWT', kid: KEY_ID })).toString('base64url');
  const payload = Buffer.from(JSON.stringify({
    iss: ISSUER_ID,
    iat: now,
    exp: now + 1200,
    aud: 'appstoreconnect-v1'
  })).toString('base64url');
  const signing = `${header}.${payload}`;
  // crypto.sign with dsaEncoding 'ieee-p1363' gives raw r||s (required for ES256 JWTs)
  const sig = crypto.sign('SHA256', Buffer.from(signing), {
    key: privateKey,
    dsaEncoding: 'ieee-p1363'
  }).toString('base64url');
  return `${signing}.${sig}`;
}

// ── HTTP helper ───────────────────────────────────────────────────────────────
function apiGet(path) {
  const token = generateJWT();
  return new Promise((resolve, reject) => {
    const opts = {
      hostname: 'api.appstoreconnect.apple.com',
      path,
      method: 'GET',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    };
    const req = https.request(opts, res => {
      let raw = '';
      res.on('data', c => raw += c);
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(raw) }); }
        catch (e) { resolve({ status: res.statusCode, body: raw }); }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

// ── Seen feedback store ───────────────────────────────────────────────────────
function loadSeen() {
  try {
    const data = JSON.parse(fs.readFileSync(SEEN_FILE, 'utf8'));
    return { items: data.items || [], seenIds: new Set((data.items || []).map(i => i.id)) };
  } catch { return { items: [], seenIds: new Set() }; }
}

function saveSeen(items) {
  fs.writeFileSync(SEEN_FILE, JSON.stringify({ lastChecked: new Date().toISOString(), items }, null, 2));
}

// ── Main ──────────────────────────────────────────────────────────────────────
async function main() {
  const jsonMode = process.argv.includes('--json');
  const log = (...a) => { if (!jsonMode) process.stderr.write(a.join(' ') + '\n'); };

  // 1. Fetch recent builds
  log('Fetching builds...');
  const buildsRes = await apiGet(`/v1/builds?filter[app]=${APP_ID}&limit=10&sort=-uploadedDate`);

  if (buildsRes.status !== 200) {
    const out = { error: `Builds API returned ${buildsRes.status}`, body: buildsRes.body };
    console.log(JSON.stringify(out, null, 2));
    process.exit(1);
  }

  const builds = buildsRes.body.data || [];
  log(`Found ${builds.length} builds`);

  // 2. Fetch feedback per build
  const { items: seenItems, seenIds } = loadSeen();
  const newFeedback = [];
  const allFeedback = [];

  for (const build of builds) {
    const buildId = build.id;
    const version = build.attributes?.version || '?';
    log(`  Checking build ${version} (${buildId})...`);

    const fbRes = await apiGet(`/v1/builds/${buildId}/betaFeedbacks?limit=25`);
    if (fbRes.status !== 200) {
      log(`    Skipped (HTTP ${fbRes.status})`);
      continue;
    }

    const feedbacks = fbRes.body.data || [];
    log(`    Found ${feedbacks.length} feedback items`);

    for (const fb of feedbacks) {
      const id = fb.id;
      const attrs = fb.attributes || {};
      const item = {
        id,
        buildId,
        buildVersion: version,
        timestamp: attrs.timestamp,
        testerEmail: attrs.email || null,
        comment: attrs.comment || '',
        deviceModel: attrs.deviceModel || null,
        osVersion: attrs.osVersion || null,
        screenshotUrl: attrs.screenshotUrl || null,
        locale: attrs.locale || null,
      };
      allFeedback.push(item);
      if (!seenIds.has(id)) newFeedback.push(item);
    }
  }

  // 3. Save updated seen list (merge new items)
  const updatedItems = [...seenItems];
  for (const item of newFeedback) {
    updatedItems.push({ ...item, classification: 'new', action: 'pending' });
  }
  saveSeen(updatedItems);

  // 4. Output
  if (jsonMode) {
    console.log(JSON.stringify({
      checkedAt: new Date().toISOString(),
      totalFeedback: allFeedback.length,
      newCount: newFeedback.length,
      newFeedback,
      allFeedback,
    }, null, 2));
  } else {
    console.log(`\n✅ Checked ${builds.length} builds`);
    console.log(`📬 Total feedback found: ${allFeedback.length}`);
    console.log(`🆕 New since last check: ${newFeedback.length}`);
    if (newFeedback.length > 0) {
      console.log('\nNew feedback:');
      for (const fb of newFeedback) {
        console.log(`  [${fb.id}] ${fb.testerEmail || 'unknown'} · build ${fb.buildVersion}`);
        console.log(`    "${fb.comment}"`);
        console.log(`    ${fb.deviceModel} / iOS ${fb.osVersion}`);
        if (fb.screenshotUrl) console.log(`    Screenshot: ${fb.screenshotUrl}`);
      }
    }
  }
}

main().catch(err => {
  console.error('Fatal:', err.message);
  process.exit(1);
});
