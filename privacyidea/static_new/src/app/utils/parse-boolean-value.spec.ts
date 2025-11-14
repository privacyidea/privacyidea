import { parseBooleanValue } from "./parse-boolean-value";
import { assert } from "./assert";

// Mock the assert function to prevent tests from crashing
jest.mock("./assert", () => ({
  assert: jest.fn((condition: boolean, message?: string) => {
    if (!condition) {
      throw new Error(message || "Assertion failed");
    }
  })
}));

describe("parseBooleanValue", () => {
  beforeEach(() => {
    // Clear mock calls before each test
    (assert as jest.Mock).mockClear();
  });

  // Test cases for valid boolean inputs
  it("should return true for boolean true", () => {
    expect(parseBooleanValue(true)).toBe(true);
  });

  it("should return false for boolean false", () => {
    expect(parseBooleanValue(false)).toBe(false);
  });

  // Test cases for valid number inputs
  it("should return true for number 1", () => {
    expect(parseBooleanValue(1)).toBe(true);
  });

  it("should return false for number 0", () => {
    expect(parseBooleanValue(0)).toBe(false);
  });

  // Test cases for valid string inputs (case-insensitive)
  it("should return true for string 'true'", () => {
    expect(parseBooleanValue("true")).toBe(true);
  });

  it("should return false for string 'false'", () => {
    expect(parseBooleanValue("false")).toBe(false);
  });

  it("should return true for string 'TRUE'", () => {
    expect(parseBooleanValue("TRUE")).toBe(true);
  });

  it("should return false for string 'FALSE'", () => {
    expect(parseBooleanValue("FALSE")).toBe(false);
  });

  it("should return true for string 'True'", () => {
    expect(parseBooleanValue("True")).toBe(true);
  });

  it("should return false for string 'False'", () => {
    expect(parseBooleanValue("False")).toBe(false);
  });

  // Test cases for invalid inputs
  it("should call assert for an invalid number", () => {
    const errMsg = "Initial value for BoolSelectButtonsComponent must be 0 or 1 if number, but was 2";
    expect(() => parseBooleanValue(2)).toThrow(errMsg);
    expect(assert).toHaveBeenCalledWith(false, errMsg);
  });

  it("should call assert for an invalid string", () => {
    const errMsg = 'Initial value for BoolSelectButtonsComponent must be "true" or "false" if string, but was invalid';
    expect(() => parseBooleanValue("invalid")).toThrow(errMsg);
    expect(assert).toHaveBeenCalledWith(false, errMsg);
  });

  it("should call assert for null", () => {
    const errMsg =
      'Initial value for BoolSelectButtonsComponent must be boolean, 0, 1, "true" or "false", but was null';
    expect(() => parseBooleanValue(null as any)).toThrow(errMsg);
    expect(assert).toHaveBeenCalledWith(false, errMsg);
  });

  it("should call assert for undefined", () => {
    const errMsg =
      'Initial value for BoolSelectButtonsComponent must be boolean, 0, 1, "true" or "false", but was undefined';
    expect(() => parseBooleanValue(undefined as any)).toThrow(errMsg);
    expect(assert).toHaveBeenCalledWith(false, errMsg);
  });

  it("should call assert for an object", () => {
    const obj = {};
    const errMsg = `Initial value for BoolSelectButtonsComponent must be boolean, 0, 1, "true" or "false", but was ${obj}`;
    expect(() => parseBooleanValue(obj as any)).toThrow(errMsg);
    expect(assert).toHaveBeenCalledWith(false, errMsg);
  });
});
