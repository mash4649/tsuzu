import { useState } from "react";
import {
  checkDesktopRuntime,
  type DesktopRuntimeStatus,
} from "./application/checkDesktopRuntime";
import "./App.css";

function App({
  captureTextSource,
}: {
  captureTextSource(text: string): Promise<{ objectId: string }>;
}) {
  const [runtimeStatus, setRuntimeStatus] = useState<DesktopRuntimeStatus>(
    "not-checked",
  );
  const [sourceText, setSourceText] = useState("");
  const [captureStatus, setCaptureStatus] = useState("未記録");

  async function handleRuntimeCheck() {
    setRuntimeStatus(await checkDesktopRuntime());
  }

  async function handleCapture() {
    setCaptureStatus("保存中…");
    try {
      const captured = await captureTextSource(sourceText);
      setCaptureStatus(`保存・再読込・検証済み: ${captured.objectId}`);
      setSourceText("");
    } catch (error) {
      setCaptureStatus(
        error instanceof Error ? `保存を停止: ${error.message}` : `保存を停止: ${String(error)}`,
      );
    }
  }

  return (
    <main className="shell">
      <p className="eyebrow">TSUZU</p>
      <h1>デスクトップ基盤</h1>
      <p>
        React と TypeScript をアプリケーションの中心に置くための、最小の
        Tauri v2 シェルです。
      </p>
      <button type="button" onClick={handleRuntimeCheck}>
        ネイティブ境界を確認
      </button>
      <p aria-live="polite">{runtimeStatusLabel(runtimeStatus)}</p>
      <section aria-labelledby="capture-title">
        <h2 id="capture-title">Canonical SOURCE</h2>
        <label htmlFor="source-text">ローカルテキスト</label>
        <textarea
          id="source-text"
          value={sourceText}
          onChange={(event) => setSourceText(event.target.value)}
          rows={4}
        />
        <button type="button" onClick={handleCapture}>
          保存して再検証
        </button>
        <p aria-live="polite">{captureStatus}</p>
      </section>
    </main>
  );
}

function runtimeStatusLabel(status: DesktopRuntimeStatus): string {
  switch (status) {
    case "ready":
      return "ネイティブ境界: 利用可能";
    case "unavailable":
      return "ネイティブ境界: 利用できません";
    case "not-checked":
      return "ネイティブ境界: 未確認";
  }
}

export default App;
