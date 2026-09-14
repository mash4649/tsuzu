import {
  requestRuntimeHealth,
  type RuntimeHealth,
} from "../platform/tauri/runtimeHealth";

export type DesktopRuntimeStatus = "not-checked" | "ready" | "unavailable";

export async function checkDesktopRuntime(): Promise<DesktopRuntimeStatus> {
  try {
    const health: RuntimeHealth = await requestRuntimeHealth();
    return resolveDesktopRuntimeStatus(health);
  } catch {
    return "unavailable";
  }
}

export function resolveDesktopRuntimeStatus(
  response: unknown,
): Exclude<DesktopRuntimeStatus, "not-checked"> {
  if (
    typeof response === "object" &&
    response !== null &&
    (response as { status?: unknown }).status === "ready"
  ) {
    return "ready";
  }

  return "unavailable";
}
