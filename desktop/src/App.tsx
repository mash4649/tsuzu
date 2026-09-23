import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
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
    setCaptureStatus("下書き保存中…");
    try {
      const captured = await captureTextSource(sourceText);
      setCaptureStatus(`下書き保存済み。Coreへ送信中… ${captured.objectId}`);
      const result = await invoke<{ output: string }>("process_desktop_ingress");
      const receipts = JSON.parse(result.output) as Array<{
        draft_id?: string | null;
        status: string;
        source_id?: string | null;
        reason?: string;
      }>;
      const receipt = receipts.find((entry) => entry.draft_id === captured.objectId);
      const committed = Boolean(
        receipt && ["COMMITTED", "ALREADY_COMMITTED"].includes(receipt.status),
      );
      if (committed && receipt) {
        setCaptureStatus(`Core保存・索引反映済み: ${receipt.source_id ?? captured.objectId}`);
      } else if (receipt && ["QUEUED", "ALREADY_QUEUED"].includes(receipt.status)) {
        setCaptureStatus(`Core受付済み・未確定: ${receipt.status}`);
      } else if (receipt?.status.startsWith("REJECTED")) {
        setCaptureStatus(`Coreが受付を停止: ${receipt.reason || receipt.status}`);
      } else if (receipt) {
        setCaptureStatus(`Core処理を確認してください: ${receipt.status}`);
      } else {
        setCaptureStatus(`下書き保存・再読込・検証済み: ${captured.objectId}`);
      }
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
        <h2 id="capture-title">Capture draft</h2>
        <p>入力は下書きとして検証された後、Mac TSUZU Coreの受付・保存状態を表示します。</p>
        <label htmlFor="source-text">保存するテキスト</label>
        <textarea
          id="source-text"
          value={sourceText}
          onChange={(event) => setSourceText(event.target.value)}
          rows={4}
        />
        <button type="button" onClick={handleCapture}>
          保存してCoreに記録
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
