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
