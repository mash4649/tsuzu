import {
  BaseDirectory,
  exists,
  mkdir,
  readFile,
  readTextFile,
  writeFile,
  writeTextFile,
} from "@tauri-apps/plugin-fs";
import type { CaptureDraftStorage } from "../../application/canonicalSourceStore";

const options = { baseDir: BaseDirectory.AppLocalData } as const;

export const captureDraftStorage: CaptureDraftStorage = {
  exists: (path) => exists(path, options),
  mkdir: (path) => mkdir(path, { ...options, recursive: true }),
  readText: (path) => readTextFile(path, options),
  writeText: (path, contents) => writeTextFile(path, contents, options),
  readBytes: (path) => readFile(path, options),
  writeBytes: (path, contents) => writeFile(path, contents, options),
};
