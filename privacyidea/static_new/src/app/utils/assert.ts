import { isDevMode } from "@angular/core";

export function assert(condition: boolean, message: string): void {
  if (isDevMode() && !condition) throw new Error(`Assertion failed: ${message}`);
}
