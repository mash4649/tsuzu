import { describe, expect, it } from "vitest";
import {
  ExistingCanonicalLayoutError,
  createCanonicalSourceStore,
  type CanonicalStorage,
} from "./canonicalSourceStore";

class MemoryStorage implements CanonicalStorage {
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

describe("CanonicalSourceStore", () => {
  it("initializes only an empty app storage, then captures and validates a SOURCE after reopen", async () => {
    const storage = new MemoryStorage();
    const ids = ["00000000-0000-4000-8000-000000000001"];
    const now = "2026-09-14T00:00:00.000Z";

    const firstRun = await createCanonicalSourceStore(storage, {
      createId: () => ids.shift()!,
      now: () => now,
    });
    const captured = await firstRun.captureText("TSUZU の記録");

    const reopened = await createCanonicalSourceStore(storage, {
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
    const store = await createCanonicalSourceStore(new MemoryStorage());
    await expect(store.captureText("default id")).resolves.toMatchObject({
      objectId: expect.stringMatching(/^[0-9a-f-]{36}$/),
    });
  });

  it("stops without modifying a Canonical layout it did not initialize", async () => {
    const storage = new MemoryStorage();
    storage.directories.add("canonical");

    await expect(createCanonicalSourceStore(storage)).rejects.toBeInstanceOf(
      ExistingCanonicalLayoutError,
    );
    expect(storage.directories).toEqual(new Set(["canonical"]));
    expect(storage.textFiles).toEqual(new Map());
  });

  it("rejects a SOURCE whose payload no longer matches its manifest", async () => {
    const storage = new MemoryStorage();
    const store = await createCanonicalSourceStore(storage, {
      createId: () => "00000000-0000-4000-8000-000000000003",
      now: () => "2026-09-14T00:00:00.000Z",
    });
    const captured = await store.captureText("intact");
    await storage.writeBytes(
      `canonical/sources/${captured.objectId}/payload/original`,
      new TextEncoder().encode("tampered"),
    );

    await expect(store.read(captured.objectId)).rejects.toThrow(
      "payload integrity mismatch",
    );
  });
});
