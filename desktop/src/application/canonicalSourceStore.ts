import {
  createTextSource,
  parseSourceManifest,
  serializeSourceManifest,
  validateSourcePayload,
  type SourceManifest,
} from "../domain/source";

const draftRoot = "capture-drafts";
const layoutMarkerPath = `${draftRoot}/layout.json`;
const layoutMarker = JSON.stringify({ format: "tsuzu-capture-draft-v1" });

export interface CaptureDraftStorage {
  exists(path: string): Promise<boolean>;
  mkdir(path: string): Promise<void>;
  readText(path: string): Promise<string>;
  writeText(path: string, contents: string): Promise<void>;
  readBytes(path: string): Promise<Uint8Array>;
  writeBytes(path: string, contents: Uint8Array): Promise<void>;
}

export class ExistingCaptureDraftLayoutError extends Error {
  constructor() {
    super("Existing capture-draft layout was not initialized by this app; refusing to modify it");
  }
}

export type CaptureDraftStore = Readonly<{
  captureText(text: string): Promise<{ objectId: string }>;
  read(objectId: string): Promise<{ manifest: SourceManifest; payload: Uint8Array }>;
}>;

export async function createCaptureDraftStore(
  storage: CaptureDraftStorage,
  dependencies: { createId?: () => string; now?: () => string } = {},
): Promise<CaptureDraftStore> {
  const createId = dependencies.createId ?? (() => crypto.randomUUID());
  const now = dependencies.now ?? (() => new Date().toISOString());

  if (!(await storage.exists(draftRoot))) {
    await storage.mkdir(draftRoot);
    await storage.mkdir(`${draftRoot}/sources`);
    await storage.writeText(layoutMarkerPath, layoutMarker);
  } else if (!(await storage.exists(layoutMarkerPath))) {
    throw new ExistingCaptureDraftLayoutError();
  } else if ((await storage.readText(layoutMarkerPath)) !== layoutMarker) {
    throw new ExistingCaptureDraftLayoutError();
  }

  return {
    async captureText(text: string) {
      assertClearText(text);
      const { manifest, payload } = await createTextSource(text, {
        objectId: createId(),
        capturedAt: now(),
      });
      const sourceRoot = `${draftRoot}/sources/${manifest.object_id}`;
      if (await storage.exists(sourceRoot)) {
        throw new Error("SOURCE identifier collision");
      }
      await storage.mkdir(sourceRoot);
      await storage.mkdir(`${sourceRoot}/payload`);
      await storage.writeBytes(`${sourceRoot}/payload/original`, payload);
      await storage.writeText(`${sourceRoot}/source.md`, serializeSourceManifest(manifest));
      return { objectId: manifest.object_id };
    },
    async read(objectId: string) {
      const sourceRoot = `${draftRoot}/sources/${objectId}`;
      const manifest = parseSourceManifest(await storage.readText(`${sourceRoot}/source.md`));
      if (manifest.object_id !== objectId) {
        throw new Error("SOURCE identifier does not match its path");
      }
      const payload = await storage.readBytes(`${sourceRoot}/${manifest.source.payload_path}`);
      await validateSourcePayload(manifest, payload);
      return { manifest, payload };
    },
  };
}

function assertClearText(text: string): void {
  const patterns = [
    /-----BEGIN(?: [A-Z0-9]+)* PRIVATE KEY-----/,
    /-----BEGIN OPENSSH PRIVATE KEY-----/,
    /(?:sk-|ghp_|xox[baprs]-|AKIA)[A-Za-z0-9_-]{16,}/,
    /\bBearer\s+[A-Za-z0-9._~-]{16,}/,
    /\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b/,
    /\b(?:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*["']?[A-Za-z0-9_./+=:-]{16,}/i,
  ];
  if (patterns.some((pattern) => pattern.test(text))) {
    throw new Error("secret guard blocked input");
  }
  for (const candidate of text.match(/https?:\/\/[^\s<>"']+/gi) ?? []) {
    let url: URL;
    try {
      url = new URL(candidate);
    } catch {
      continue;
    }
    if (url.username || url.password || [...url.searchParams].some(([key, value]) => ["access_token", "api_key", "apikey", "signature", "sig", "token"].includes(key.toLowerCase()) && value.length >= 16)) {
      throw new Error("secret guard blocked input");
    }
  }
}
