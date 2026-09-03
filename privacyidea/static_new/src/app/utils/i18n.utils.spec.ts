/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
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
import { formatList, labelWithColon, pluralize } from "./i18n.utils";

describe("i18n.utils", () => {
  describe("labelWithColon", () => {
    it("appends the locale's label separator", () => {
      expect(labelWithColon("Username")).toBe("Username:");
    });
  });

  describe("pluralize", () => {
    const forms = { one: "one token", other: "many tokens" };

    it("selects the matching form for the given locale and count", () => {
      expect(pluralize("en", 1, forms)).toBe("one token");
      expect(pluralize("en", 5, forms)).toBe("many tokens");
    });

    it("falls back to the other form when the locale's category isn't provided", () => {
      // Russian distinguishes "few"/"many" categories that these forms don't supply.
      expect(pluralize("ru", 2, forms)).toBe("many tokens");
    });

    it("uses the few/many forms when provided", () => {
      const fullForms = { one: "one", few: "few", many: "many", other: "other" };
      expect(pluralize("ru", 2, fullForms)).toBe("few");
      expect(pluralize("ru", 5, fullForms)).toBe("many");
    });
  });

  describe("formatList", () => {
    it("joins items with the locale's conjunction list separator", () => {
      expect(formatList("en", ["a", "b", "c"])).toBe("a, b, and c");
    });

    it("returns a single item unchanged", () => {
      expect(formatList("en", ["a"])).toBe("a");
    });
  });
});
