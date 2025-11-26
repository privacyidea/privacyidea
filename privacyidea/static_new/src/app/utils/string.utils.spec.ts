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

import { StringUtils } from "./string.utils";

describe("StringUtils", () => {
  it("should replace tags in template string with provided values", () => {
    const template = "Token with serial {{ serial }} successfully enrolled for user {{user}}.";
    const tagData = {
      serial: "1234",
      user: "alice"
    };
    const result = StringUtils.replaceWithTags(template, tagData);
    expect(result).toBe("Token with serial 1234 successfully enrolled for user alice.");
  });

  describe("splitOnce", () => {
    it("should split at the first occurrence of the delimiter", () => {
      const result = StringUtils.splitOnce("foo:bar:baz", ":");
      expect(result).toEqual({ head: "foo", tail: "bar:baz" });
    });

    it("should return the original string and empty tail if delimiter not found", () => {
      const result = StringUtils.splitOnce("foobar", ":");
      expect(result).toEqual({ head: "foobar", tail: "" });
    });

    it("should handle empty string input", () => {
      const result = StringUtils.splitOnce("", ":");
      expect(result).toEqual({ head: "", tail: "" });
    });

    it("should handle empty delimiter (returns whole string as head, empty tail)", () => {
      const result = StringUtils.splitOnce("foo", "");
      expect(result).toEqual({ head: "", tail: "foo" });
    });

    it("should handle delimiter at the start", () => {
      const result = StringUtils.splitOnce(":foo:bar", ":");
      expect(result).toEqual({ head: "", tail: "foo:bar" });
    });

    it("should handle delimiter at the end", () => {
      const result = StringUtils.splitOnce("foo:", ":");
      expect(result).toEqual({ head: "foo", tail: "" });
    });

    it("should handle multi-character delimiter", () => {
      const result = StringUtils.splitOnce("foo--bar--baz", "--");
      expect(result).toEqual({ head: "foo", tail: "bar--baz" });
    });
    it("should handle string with only the delimiter", () => {
      const result = StringUtils.splitOnce("::", ":");
      expect(result).toEqual({ head: "", tail: ":" });
    });
    it("should handle string with multiple consecutive delimiters", () => {
      const result = StringUtils.splitOnce("foo:::bar", ":");
      expect(result).toEqual({ head: "foo", tail: "::bar" });
    });
  });
});
