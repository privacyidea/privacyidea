/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { parseBooleanValue } from "./parse-boolean-value";
import { assert } from "./assert";

jest.mock("./assert", () => ({
  assert: jest.fn((condition: boolean, message?: string) => {
    if (!condition) {
      throw new Error(message || "Assertion failed");
    }
  })
}));

describe("parseBooleanValue", () => {
  beforeEach(() => {
    (assert as jest.Mock).mockClear();
  });

  it("should return true for boolean true", () => {
    expect(parseBooleanValue(true)).toBe(true);
  });

  it("should return false for boolean false", () => {
    expect(parseBooleanValue(false)).toBe(false);
  });

  it("should return true for number 1", () => {
    expect(parseBooleanValue(1)).toBe(true);
  });

  it("should return false for number 0", () => {
    expect(parseBooleanValue(0)).toBe(false);
  });

  it("should return true for string 'true'", () => {
    expect(parseBooleanValue("true")).toBe(true);
  });

  it("should return false for string 'false'", () => {
    expect(parseBooleanValue("false")).toBe(false);
  });

  it("should return true for string '1'", () => {
    expect(parseBooleanValue("1")).toBe(true);
  });

  it("should return false for string '0'", () => {
    expect(parseBooleanValue("0")).toBe(false);
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
    const errMsg = "Initial value for parseBooleanValue must be 0 or 1 if number, but was 2";
    expect(() => parseBooleanValue(2)).toThrow(errMsg);
    expect(assert).toHaveBeenCalledWith(false, errMsg);
  });

  it("should call assert for an invalid string", () => {
    const errMsg = "Initial value for parseBooleanValue must be \"true\", \"false\", \"1\" or \"0\" if string, but was invalid";
    expect(() => parseBooleanValue("invalid")).toThrow(errMsg);
    expect(assert).toHaveBeenCalledWith(false, errMsg);
  });

  it("should call assert for null", () => {
    const errMsg =
      "Initial value for parseBooleanValue must be boolean, 0, 1, \"true\", \"false\", \"1\" or \"0\", but was null";
    expect(() => parseBooleanValue(null as any)).toThrow(errMsg);
    expect(assert).toHaveBeenCalledWith(false, errMsg);
  });

  it("should call assert for undefined", () => {
    const errMsg =
      "Initial value for parseBooleanValue must be boolean, 0, 1, \"true\", \"false\", \"1\" or \"0\", but was undefined";
    expect(() => parseBooleanValue(undefined as any)).toThrow(errMsg);
    expect(assert).toHaveBeenCalledWith(false, errMsg);
  });

  it("should call assert for an object", () => {
    const obj = {};
    const errMsg = `Initial value for parseBooleanValue must be boolean, 0, 1, "true", "false", "1" or "0", but was ${obj}`;
    expect(() => parseBooleanValue(obj as any)).toThrow(errMsg);
    expect(assert).toHaveBeenCalledWith(false, errMsg);
  });
});
