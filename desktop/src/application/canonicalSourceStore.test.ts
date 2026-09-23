import { describe, expect, it } from "vitest";
import {
  ExistingCaptureDraftLayoutError,
  createCaptureDraftStore,
  type CaptureDraftStorage,
} from "./canonicalSourceStore";

class MemoryStorage implements CaptureDraftStorage {
  readonly directories = new Set<string>();
  readonly textFiles = new Map<string, string>();
  readonly binaryFiles = new Map<string, Uint8Array>();

  async exists(path: string): Promise<boolean> {
    return (
      this.directories.has(path) ||
      this.textFiles.has(path) ||
      this.binaryFiles.has(path)
    );
  }

  async mkdir(path: string): Promise<void> {
    this.directories.add(path);
  }

  async readText(path: string): Promise<string> {
    const value = this.textFiles.get(path);
    if (value === undefined) throw new Error(`Missing text file: ${path}`);
    return value;
  }

  async writeText(path: string, contents: string): Promise<void> {
    this.textFiles.set(path, contents);
  }

  async readBytes(path: string): Promise<Uint8Array> {
    const value = this.binaryFiles.get(path);
    if (value === undefined) throw new Error(`Missing binary file: ${path}`);
    return value;
  }

  async writeBytes(path: string, contents: Uint8Array): Promise<void> {
    this.binaryFiles.set(path, contents);
  }
}

describe("CaptureDraftStore", () => {
  it("initializes only an empty app storage, then captures and validates a SOURCE after reopen", async () => {
    const storage = new MemoryStorage();
    const ids = ["00000000-0000-4000-8000-000000000001"];
    const now = "2026-09-14T00:00:00.000Z";

    const firstRun = await createCaptureDraftStore(storage, {
      createId: () => ids.shift()!,
      now: () => now,
    });
    const captured = await firstRun.captureText("TSUZU の記録");

    const reopened = await createCaptureDraftStore(storage, {
      createId: () => "00000000-0000-4000-8000-000000000002",
      now: () => now,
    });
    await expect(reopened.read(captured.objectId)).resolves.toMatchObject({
      manifest: {
        object_id: "00000000-0000-4000-8000-000000000001",
        object_type: "SOURCE",
        source: { payload_bytes: 15 },
      },
      payload: new TextEncoder().encode("TSUZU の記録"),
    });
  });

  it("creates a SOURCE with the platform UUID generator by default", async () => {
    const store = await createCaptureDraftStore(new MemoryStorage());
    await expect(store.captureText("default id")).resolves.toMatchObject({
      objectId: expect.stringMatching(/^[0-9a-f-]{36}$/),
    });
  });

  it("stops without modifying a capture-draft layout it did not initialize", async () => {
    const storage = new MemoryStorage();
    storage.directories.add("capture-drafts");

    await expect(createCaptureDraftStore(storage)).rejects.toBeInstanceOf(
      ExistingCaptureDraftLayoutError,
    );
    expect(storage.directories).toEqual(new Set(["capture-drafts"]));
    expect(storage.textFiles).toEqual(new Map());
  });

  it("rejects a SOURCE whose payload no longer matches its manifest", async () => {
    const storage = new MemoryStorage();
    const store = await createCaptureDraftStore(storage, {
      createId: () => "00000000-0000-4000-8000-000000000003",
      now: () => "2026-09-14T00:00:00.000Z",
    });
    const captured = await store.captureText("intact");
    await storage.writeBytes(
      `capture-drafts/sources/${captured.objectId}/payload/original`,
      new TextEncoder().encode("tampered"),
    );

    await expect(store.read(captured.objectId)).rejects.toThrow(
      "payload integrity mismatch",
    );
  });

  it("refuses restricted text before creating a durable capture draft", async () => {
    const storage = new MemoryStorage();
    const store = await createCaptureDraftStore(storage);

    await expect(store.captureText("api_key=abcdefghijklmnopqrstuvwxyz")).rejects.toThrow(
      "secret guard blocked input",
    );
    expect(storage.binaryFiles).toEqual(new Map());
  });
});
