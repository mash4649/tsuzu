import { describe, expect, test } from "vitest";
import { resolveDesktopRuntimeStatus } from "./checkDesktopRuntime";

describe("resolveDesktopRuntimeStatus", () => {
  test("accepts the only supported native health response", () => {
    expect(resolveDesktopRuntimeStatus({ status: "ready" })).toBe("ready");
  });

  test("maps an unexpected native response to an unavailable state", () => {
    expect(resolveDesktopRuntimeStatus({ status: "other" })).toBe("unavailable");
  });
});
