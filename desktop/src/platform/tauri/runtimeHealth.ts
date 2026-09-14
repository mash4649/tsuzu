import { invoke } from "@tauri-apps/api/core";

export type RuntimeHealth = Readonly<{
  status: "ready";
}>;

export function requestRuntimeHealth(): Promise<RuntimeHealth> {
  return invoke<RuntimeHealth>("runtime_health");
}
