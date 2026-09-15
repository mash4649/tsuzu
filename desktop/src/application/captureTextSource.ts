import {
  createCanonicalSourceStore,
  type CanonicalStorage,
} from "./canonicalSourceStore";

export function createCaptureTextSourceService(storage: CanonicalStorage) {
  const store = createCanonicalSourceStore(storage);

  return async (text: string): Promise<{ objectId: string }> => {
    if (!text.trim()) throw new Error("記録するテキストを入力してください");
    const captured = await (await store).captureText(text);
    await (await store).read(captured.objectId);
    return captured;
  };
}
