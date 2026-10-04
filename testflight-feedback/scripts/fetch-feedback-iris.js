#!/usr/bin/env node
/**
 * fetch-feedback-iris.js
 * Fetches TestFlight beta feedback via Apple's iris API using
 * the FASTLANE_SESSION cookie jar (~30 day session, no browser).
 *
 * Usage: node fetch-feedback-iris.js [--json]
 *
 * Session refresh: run `fastlane spaceauth -u divyamrastogi2@gmail.com`
 * every ~30 days and save output to references/.fastlane_session
 */

const fs   = require('fs');
const dns  = require('dns');
const https = require('https');
const path  = require('path');

// ── Config ────────────────────────────────────────────────────────────────────
const HOSTNAME     = 'appstoreconnect.apple.com';
const APP_ID       = '6759486622';
const SESSION_FILE = path.join(__dirname, '../references/.fastlane_session');
const SEEN_FILE    = path.join(__dirname, '../references/seen-feedback.json');

// ── DNS resolve (system resolver works, Node default may not) ─────────────────
function resolveHost(hostname) {
  return new Promise((resolve, reject) => {
    dns.resolve4(hostname, (err, addrs) => {
      if (err) reject(err);
      else resolve(addrs[0]);
    });
  });
}

// ── Parse FASTLANE_SESSION YAML → cookie string ───────────────────────────────
function loadCookies() {
  const raw = fs.readFileSync(SESSION_FILE, 'utf8');
  const cookies = [];
  const blocks = raw.split(/^- !ruby\/object:HTTP::Cookie/m).slice(1);
  for (const block of blocks) {
    const nameMatch  = block.match(/^\s+name:\s+(.+)$/m);
    const valueMatch = block.match(/^\s+value:\s+(.+)$/m);
    if (nameMatch && valueMatch) {
      cookies.push({ name: nameMatch[1].trim(), value: valueMatch[1].trim() });
    }
  }
  if (!cookies.length) throw new Error('No cookies found in session file');
  return cookies.map(c => `${c.name}=${c.value}`).join('; ');
}

// ── HTTP helper (uses resolved IP + Host header to bypass Node DNS issue) ─────
function irisGet(ipAddr, pathStr, cookieHeader) {
  return new Promise((resolve, reject) => {
    const req = https.request({
      hostname: ipAddr,
      port: 443,
      path: pathStr,
      method: 'GET',
      headers: {
        'Host': HOSTNAME,
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Cookie': cookieHeader,
      }
    }, res => {
      let raw = '';
      res.on('data', c => raw += c);
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(raw) }); }
        catch { resolve({ status: res.statusCode, body: raw }); }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

// ── Refresh dqsid: exchange myacinfo for a fresh session cookie ───────────────
// dqsid has max_age: 1800 (30 min) — we must refresh it before each run
function refreshSession(ipAddr, cookieHeader) {
  return new Promise((resolve, reject) => {
    const req = https.request({
      hostname: ipAddr,
      port: 443,
      path: '/',
      method: 'GET',
      headers: {
        'Host': HOSTNAME,
        'Accept': 'text/html',
        'Cookie': cookieHeader,
      }
    }, res => {
      // Extract fresh dqsid from Set-Cookie header
      const setCookies = res.headers['set-cookie'] || [];
      let freshDqsid = null;
      for (const c of setCookies) {
        const m = c.match(/^dqsid=([^;]+)/);
        if (m) { freshDqsid = m[1]; break; }
      }
      res.resume(); // drain response body
      resolve(freshDqsid);
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
  fs.writeFileSync(SEEN_FILE, JSON.stringify({
    lastChecked: new Date().toISOString(), items
  }, null, 2));
}

// ── Parse iris response into flat feedback objects ────────────────────────────
function parseResponse(body, type, seenIds, newFeedback, allFeedback) {
  const data     = body.data     || [];
  const included = body.included || [];

  const testers = {};
  const builds  = {};
  for (const inc of included) {
    if (inc.type === 'betaTesters') testers[inc.id] = inc.attributes;
    if (inc.type === 'builds')      builds[inc.id]  = inc.attributes;
  }

  for (const item of data) {
    const attrs     = item.attributes || {};
    const testerRel = item.relationships?.tester?.data;
    const buildRel  = item.relationships?.build?.data;
    const tester    = testerRel ? testers[testerRel.id] : null;
    const build     = buildRel  ? builds[buildRel.id]   : null;

    const fb = {
      id:           item.id,
      type,
      timestamp:    attrs.timestamp,
      comment:      attrs.comment || '',
      deviceModel:  attrs.deviceModel || null,
      osVersion:    attrs.osVersion || null,
      locale:       attrs.locale || null,
      appVersion:   build?.version || null,
      testerName:   tester ? `${tester.firstName||''} ${tester.lastName||''}`.trim() : null,
      testerEmail:  attrs.emailAddress || tester?.email || null,
      screenshotIds: (item.relationships?.screenshots?.data || []).map(s => s.id),
    };
    allFeedback.push(fb);
    if (!seenIds.has(fb.id)) newFeedback.push(fb);
  }
}

// ── Main ──────────────────────────────────────────────────────────────────────
async function main() {
  const jsonMode = process.argv.includes('--json');
  const log = (...a) => { if (!jsonMode) process.stderr.write(a.join(' ') + '\n'); };

  // Load cookies
  log('Loading session...');
  let cookieHeader;
  try { cookieHeader = loadCookies(); }
  catch (e) { console.error('Session error:', e.message); process.exit(1); }

  // Resolve IP
  log(`Resolving ${HOSTNAME}...`);
  let ipAddr;
  try { ipAddr = await resolveHost(HOSTNAME); log(`  → ${ipAddr}`); }
  catch (e) { console.error('DNS error:', e.message); process.exit(1); }

  // Refresh dqsid (it only lasts 30 min; myacinfo is long-lived)
  log('Refreshing session (dqsid)...');
  const freshDqsid = await refreshSession(ipAddr, cookieHeader);
  if (freshDqsid) {
    // Replace old dqsid with fresh one
    cookieHeader = cookieHeader.replace(/dqsid=[^;]+(; )?/, '').replace(/; $/, '');
    cookieHeader = cookieHeader + `; dqsid=${freshDqsid}`;
    log('  → dqsid refreshed ✓');
  } else {
    log('  → no new dqsid in response, using existing (may be expired)');
  }

  // Fetch screenshot feedback
  log('Fetching screenshot feedback...');
  const screenshotPath = `/iris/v1/betaFeedbacks?filter%5Bbuild.app%5D=${APP_ID}&sort=-timestamp&exists%5Bcrash%5D=false&include=tester,build,screenshots,buildBundle&fields%5BbetaTesters%5D=firstName,lastName&fields%5Bbuilds%5D=version&limit=60`;
  const ssRes = await irisGet(ipAddr, screenshotPath, cookieHeader);

  if (ssRes.status === 401 || ssRes.status === 403) {
    console.error(`❌ Session expired (HTTP ${ssRes.status}). Run: fastlane spaceauth -u divyamrastogi2@gmail.com`);
    process.exit(2);
  }
  if (ssRes.status !== 200) {
    console.error(`Unexpected status ${ssRes.status}:`, JSON.stringify(ssRes.body).substring(0, 300));
    process.exit(1);
  }

  // Fetch crash feedback
  log('Fetching crash feedback...');
  const crashPath = `/iris/v1/betaFeedbacks?filter%5Bbuild.app%5D=${APP_ID}&sort=-timestamp&exists%5Bcrash%5D=true&include=tester,build,screenshots,buildBundle&fields%5BbetaTesters%5D=firstName,lastName&fields%5Bbuilds%5D=version&limit=60`;
  const crashRes = await irisGet(ipAddr, crashPath, cookieHeader);

  // Parse
  const { items: seenItems, seenIds } = loadSeen();
  const allFeedback = [], newFeedback = [];
  parseResponse(ssRes.body, 'screenshot', seenIds, newFeedback, allFeedback);
  if (crashRes.status === 200) parseResponse(crashRes.body, 'crash', seenIds, newFeedback, allFeedback);

  // Save
  const updatedItems = [
    ...seenItems.filter(i => !allFeedback.some(n => n.id === i.id)), // keep manual entries not returned by API
    ...allFeedback.map(fb => ({
      ...fb,
      classification: seenIds.has(fb.id)
        ? (seenItems.find(i => i.id === fb.id)?.classification || 'seen')
        : 'new',
      action: seenIds.has(fb.id)
        ? (seenItems.find(i => i.id === fb.id)?.action || 'none')
        : 'pending',
    }))
  ];
  saveSeen(updatedItems);

  // Output
  if (jsonMode) {
    console.log(JSON.stringify({
      checkedAt: new Date().toISOString(),
      totalFeedback: allFeedback.length,
      newCount: newFeedback.length,
      newFeedback,
      allFeedback,
    }, null, 2));
  } else {
    console.log(`\n✅ Iris API connected`);
    console.log(`📬 Total feedback: ${allFeedback.length}`);
    console.log(`🆕 New since last check: ${newFeedback.length}`);
    for (const fb of allFeedback) {
      const isNew = newFeedback.some(n => n.id === fb.id) ? ' 🆕' : '';
      console.log(`\n  [${fb.type}]${isNew} ${fb.testerName || fb.testerEmail || 'unknown'} · build ${fb.appVersion}`);
      if (fb.comment) console.log(`  "${fb.comment}"`);
      console.log(`  ${fb.deviceModel} / iOS ${fb.osVersion} · ${fb.timestamp}`);
    }
  }
}

main().catch(err => { console.error('Fatal:', err.message); process.exit(1); });
