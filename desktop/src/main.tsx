import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { createCaptureTextSourceService } from "./application/captureTextSource";
import { canonicalStorage } from "./platform/tauri/canonicalStorage";

const captureTextSource = createCaptureTextSourceService(canonicalStorage);

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App captureTextSource={captureTextSource} />
  </React.StrictMode>,
);
