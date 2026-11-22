import { copyFileSync, mkdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const sourceDir = process.env.MAKEFUN_BOT_DIR ?? "/bot";
const targetDir = process.env.MAKEFUN_OUTPUT_DIR ?? "/output";
const fileName = "POST.json";
const sourcePath = join(sourceDir, fileName);
const targetPath = join(targetDir, fileName);

function fail(reason: string): never {
  console.error(`POST.json rejected: ${reason}`);
  process.exit(1);
}

let rawBytes: Buffer;
try {
  rawBytes = readFileSync(sourcePath);
} catch (err) {
  console.error(
    `Unable to read POST.json from ${sourceDir}: ${(err as Error).message}`,
  );
  process.exit(1);
}

let parsed: unknown;
try {
  parsed = JSON.parse(rawBytes.toString("utf8"));
} catch (err) {
  fail(`file is not valid JSON (${(err as Error).message})`);
}

if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
  fail("top-level value must be a JSON object");
}

const urlValue = (parsed as Record<string, unknown>)["url"];
if (typeof urlValue !== "string" || urlValue.length === 0) {
  fail("field 'url' must be present and must be a non-empty string");
}

let link: URL;
try {
  link = new URL(urlValue);
} catch {
  fail(`url is not a well-formed URL: ${urlValue}`);
}

if (link.protocol !== "https:") {
  fail(`url must use https, got '${link.protocol.replace(/:$/, "")}'`);
}

const allowedHosts = new Set(["x.com", "twitter.com"]);
if (!allowedHosts.has(link.hostname)) {
  fail(`url host must be x.com or twitter.com, got '${link.hostname}'`);
}

const segments = link.pathname.split("/").filter((part) => part.length > 0);
if (segments.length !== 3 || segments[1] !== "status") {
  fail(
    `url path must look like /<handle>/status/<post id>, got '${link.pathname}'`,
  );
}

const handle = segments[0]!;
const postId = segments[2]!;

if (!/^[A-Za-z0-9_]{1,15}$/.test(handle)) {
  fail(
    `handle '${handle}' is invalid - use 1 to 15 letters, digits or underscores, not a placeholder`,
  );
}

if (!/^[0-9]+$/.test(postId)) {
  fail(
    `post id '${postId}' is invalid - a status id is digits only, not a placeholder`,
  );
}

try {
  mkdirSync(targetDir, { recursive: true });
} catch (err) {
  console.error(
    `Unable to prepare output directory ${targetDir}: ${(err as Error).message}`,
  );
  process.exit(1);
}

try {
  copyFileSync(sourcePath, targetPath);
} catch (err) {
  console.error(
    `Unable to copy POST.json to ${targetDir}: ${(err as Error).message}`,
  );
  process.exit(1);
}

let writtenBytes: Buffer;
try {
  writtenBytes = readFileSync(targetPath);
} catch (err) {
  console.error(
    `Unable to re-read copied POST.json in ${targetDir}: ${(err as Error).message}`,
  );
  process.exit(1);
}

if (!writtenBytes.equals(rawBytes)) {
  console.error(
    `Copied POST.json in ${targetDir} does not match the source byte-for-byte (${writtenBytes.length} bytes written, ${rawBytes.length} bytes expected)`,
  );
  process.exit(1);
}
