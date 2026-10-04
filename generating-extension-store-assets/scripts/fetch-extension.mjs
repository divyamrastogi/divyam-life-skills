#!/usr/bin/env node
// Fetch a published Chrome extension's code from a Web Store URL (or bare id)
// and unpack it into a directory, ready for --load-extension.
//
//   node fetch-extension.mjs <webstore-url-or-id> <dest-dir>
//
// Mechanics: every published extension is served as a CRX3 from Google's own
// update endpoint (the URL Chrome updates from — no auth). A CRX3 is a zip
// prefixed with a signed header: "Cr24" magic, uint32 version, uint32 header
// length, then the zip. We strip the prefix and unzip, then delete the
// store-injected _metadata/ folder (its presence breaks unpacked loading).
//
// Note: this is the BUILT artifact (possibly minified), not the source repo.

import { execFileSync } from 'node:child_process';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import os from 'node:os';

const [input, destDir] = process.argv.slice(2);
if (!input || !destDir) {
  console.error('usage: fetch-extension.mjs <webstore-url-or-id> <dest-dir>');
  process.exit(1);
}

const idMatch = /([a-p]{32})/.exec(input);
if (!idMatch) {
  console.error('could not find a 32-char extension id in: ' + input);
  process.exit(1);
}
const id = idMatch[1];

const crxUrl =
  'https://clients2.google.com/service/update2/crx' +
  '?response=redirect&prodversion=126.0.0.0&acceptformat=crx2,crx3' +
  `&x=id%3D${id}%26uc`;

console.log(`fetching ${id} ...`);
const res = await fetch(crxUrl, { redirect: 'follow' });
if (!res.ok) {
  console.error(`download failed: HTTP ${res.status} (is the id published?)`);
  process.exit(1);
}
const crx = Buffer.from(await res.arrayBuffer());

if (crx.subarray(0, 4).toString('latin1') !== 'Cr24') {
  console.error('not a CRX file (missing Cr24 magic)');
  process.exit(1);
}
const version = crx.readUInt32LE(4);
// CRX3: [magic][version][headerLen][header][zip]. CRX2: two length fields.
const zipStart =
  version === 3 ? 12 + crx.readUInt32LE(8) : 16 + crx.readUInt32LE(8) + crx.readUInt32LE(12);
const zip = crx.subarray(zipStart);

const tmpZip = path.join(os.tmpdir(), `crx-${id}.zip`);
writeFileSync(tmpZip, zip);
mkdirSync(destDir, { recursive: true });
execFileSync('unzip', ['-oq', tmpZip, '-d', destDir]);
rmSync(tmpZip, { force: true });
rmSync(path.join(destDir, '_metadata'), { recursive: true, force: true });

console.log(`unpacked ${id} (crx v${version}, ${zip.length} zip bytes) -> ${destDir}`);
