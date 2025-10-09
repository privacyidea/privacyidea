import { assert } from "./assert";

export function parseBooleanValue(initialValue: string | number | boolean): boolean {
  console.log("Parsing initialValue:", initialValue);
  const typeofInitialValue = typeof initialValue;
  if (typeofInitialValue === "boolean") {
    return !!initialValue;
  }
  if (typeofInitialValue === "number") {
    if (initialValue === 1) return true;
    if (initialValue === 0) return false;
    assert(false, `Initial value for BoolSelectButtonsComponent must be 0 or 1 if number, but was ${initialValue}`);
  }
  if (typeofInitialValue === "string") {
    if (String(initialValue).toLowerCase() === "true") return true;
    if (String(initialValue).toLowerCase() === "false") return false;
    assert(
      false,
      `Initial value for BoolSelectButtonsComponent must be "true" or "false" if string, but was ${initialValue}`
    );
  }
  assert(
    false,
    `Initial value for BoolSelectButtonsComponent must be boolean, 0, 1, "true" or "false", but was ${initialValue}`
  );
  return false;
}
