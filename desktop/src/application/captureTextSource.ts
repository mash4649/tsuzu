import {
  createCaptureDraftStore,
  type CaptureDraftStorage,
} from "./canonicalSourceStore";

export function createCaptureTextSourceService(storage: CaptureDraftStorage) {
  const store = createCaptureDraftStore(storage);

  return async (text: string): Promise<{ objectId: string }> => {
    if (!text.trim()) throw new Error("保存するテキストを入力してください");
    const captured = await (await store).captureText(text);
    await (await store).read(captured.objectId);
    return captured;
  };
}
