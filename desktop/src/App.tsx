import { useState } from "react";
import {
  checkDesktopRuntime,
  type DesktopRuntimeStatus,
} from "./application/checkDesktopRuntime";
import "./App.css";

function App() {
  const [runtimeStatus, setRuntimeStatus] = useState<DesktopRuntimeStatus>(
    "not-checked",
  );

  async function handleRuntimeCheck() {
    setRuntimeStatus(await checkDesktopRuntime());
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
