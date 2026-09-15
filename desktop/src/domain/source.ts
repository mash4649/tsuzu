const SOURCE_VERSION = "1.0.0";
const textEncoder = new TextEncoder();

export type SourceManifest = Readonly<{
  object_id: string;
  object_type: "SOURCE";
  schema_version: typeof SOURCE_VERSION;
  created_at: string;
  updated_at: string;
  revision: 1;
  scope: { scope_type: "GLOBAL"; scope_id: null };
  provenance: {
    origin: "USER_EXPLICIT";
    source_refs: string[];
    actor: "USER";
    explicitness: "EXPLICIT";
  };
  trust: { level: "ASSERTED"; confidence: 1 };
  sensitivity: { level: "PERSONAL" };
  temporal: { valid_from: null; valid_until: null };
  deletion: { state: "LIVE"; tombstoned_at: null };
  source: {
    kind: "TEXT";
    capture_method: "LOCAL_TEXT";
    media_type: "text/plain";
    encoding: "utf-8";
    original_name: null;
    origin_locator: { type: "NONE"; value: null };
    payload_path: "payload/original";
    payload_sha256: string;
    payload_bytes: number;
    captured_at: string;
  };
}>;

export class SourceValidationError extends Error {}

export async function createTextSource(
  text: string,
  { objectId, capturedAt }: { objectId: string; capturedAt: string },
): Promise<{ manifest: SourceManifest; payload: Uint8Array }> {
  const payload = textEncoder.encode(text);
  const payloadSha256 = await sha256(payload);
  const manifest: SourceManifest = {
    object_id: objectId,
    object_type: "SOURCE",
    schema_version: SOURCE_VERSION,
    created_at: capturedAt,
    updated_at: capturedAt,
    revision: 1,
    scope: { scope_type: "GLOBAL", scope_id: null },
    provenance: {
      origin: "USER_EXPLICIT",
      source_refs: [],
      actor: "USER",
      explicitness: "EXPLICIT",
    },
    trust: { level: "ASSERTED", confidence: 1 },
    sensitivity: { level: "PERSONAL" },
    temporal: { valid_from: null, valid_until: null },
    deletion: { state: "LIVE", tombstoned_at: null },
    source: {
      kind: "TEXT",
      capture_method: "LOCAL_TEXT",
      media_type: "text/plain",
      encoding: "utf-8",
      original_name: null,
      origin_locator: { type: "NONE", value: null },
      payload_path: "payload/original",
      payload_sha256: payloadSha256,
      payload_bytes: payload.byteLength,
      captured_at: capturedAt,
    },
  };
  validateSourceManifest(manifest);
  return { manifest, payload };
}

export function serializeSourceManifest(manifest: SourceManifest): string {
  validateSourceManifest(manifest);
  return `---\n${JSON.stringify(manifest, null, 2)}\n---\n`;
}

export function parseSourceManifest(document: string): SourceManifest {
  if (!document.startsWith("---\n") || !document.endsWith("\n---\n")) {
    throw new SourceValidationError("Source manifest must be JSON frontmatter");
  }
  const content = document.slice(4, -5);
  let manifest: unknown;
  try {
    manifest = JSON.parse(content);
  } catch {
    throw new SourceValidationError("Source manifest JSON is invalid");
  }
  validateSourceManifest(manifest);
  return manifest;
}

export async function validateSourcePayload(
  manifest: SourceManifest,
  payload: Uint8Array,
): Promise<void> {
  validateSourceManifest(manifest);
  if (
    payload.byteLength !== manifest.source.payload_bytes ||
    (await sha256(payload)) !== manifest.source.payload_sha256
  ) {
    throw new SourceValidationError("payload integrity mismatch");
  }
}

export function validateSourceManifest(value: unknown): asserts value is SourceManifest {
  if (!hasExactKeys(value, ["object_id", "object_type", "schema_version", "created_at", "updated_at", "revision", "scope", "provenance", "trust", "sensitivity", "temporal", "deletion", "source"])) fail("Source envelope fields are invalid");
  if (
    value.object_type !== "SOURCE" ||
    value.schema_version !== SOURCE_VERSION ||
    !isUuidV4(value.object_id) ||
    !isTimestamp(value.created_at) ||
    !isTimestamp(value.updated_at) ||
    value.revision !== 1
  ) {
    fail("Source identity fields are invalid");
  }
  if (!hasExactKeys(value.scope, ["scope_type", "scope_id"]) || value.scope.scope_type !== "GLOBAL" || value.scope.scope_id !== null) fail("Source scope is invalid");
  if (!hasExactKeys(value.provenance, ["origin", "source_refs", "actor", "explicitness"]) || value.provenance.origin !== "USER_EXPLICIT" || value.provenance.actor !== "USER" || value.provenance.explicitness !== "EXPLICIT" || !Array.isArray(value.provenance.source_refs) || !value.provenance.source_refs.every((item) => typeof item === "string")) fail("Source provenance is invalid");
  if (!hasExactKeys(value.trust, ["level", "confidence"]) || value.trust.level !== "ASSERTED" || value.trust.confidence !== 1) fail("Source trust is invalid");
  if (!hasExactKeys(value.sensitivity, ["level"]) || value.sensitivity.level !== "PERSONAL") fail("Source sensitivity is invalid");
  if (!hasExactKeys(value.temporal, ["valid_from", "valid_until"]) || value.temporal.valid_from !== null || value.temporal.valid_until !== null) fail("Source temporal metadata is invalid");
  if (!hasExactKeys(value.deletion, ["state", "tombstoned_at"]) || value.deletion.state !== "LIVE" || value.deletion.tombstoned_at !== null) fail("Source deletion metadata is invalid");
  if (!hasExactKeys(value.source, ["kind", "capture_method", "media_type", "encoding", "original_name", "origin_locator", "payload_path", "payload_sha256", "payload_bytes", "captured_at"])) fail("Source payload metadata is invalid");
  const source = value.source;
  if (
    source.kind !== "TEXT" ||
    source.capture_method !== "LOCAL_TEXT" ||
    source.media_type !== "text/plain" ||
    source.encoding !== "utf-8" ||
    source.original_name !== null ||
    !hasExactKeys(source.origin_locator, ["type", "value"]) ||
    source.origin_locator.type !== "NONE" ||
    source.origin_locator.value !== null ||
    source.payload_path !== "payload/original" ||
    typeof source.payload_sha256 !== "string" ||
    !/^[0-9a-f]{64}$/.test(source.payload_sha256) ||
    typeof source.payload_bytes !== "number" ||
    !Number.isSafeInteger(source.payload_bytes) ||
    source.payload_bytes < 0 ||
    !isTimestamp(source.captured_at)
  ) fail("Source payload metadata is invalid");
}

async function sha256(payload: Uint8Array): Promise<string> {
  const input = new ArrayBuffer(payload.byteLength);
  new Uint8Array(input).set(payload);
  const hash = await crypto.subtle.digest("SHA-256", input);
  return Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasExactKeys(value: unknown, keys: readonly string[]): value is Record<string, unknown> {
  return isRecord(value) && Object.keys(value).length === keys.length && keys.every((key) => key in value);
}

function isUuidV4(value: unknown): value is string {
  return typeof value === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(value);
}

function isTimestamp(value: unknown): value is string {
  return typeof value === "string" && !Number.isNaN(Date.parse(value)) && /(?:Z|[+-]\d\d:\d\d)$/.test(value);
}

function fail(message: string): never {
  throw new SourceValidationError(message);
}
