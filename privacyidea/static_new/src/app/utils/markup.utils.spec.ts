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

import { splitMarkupSegments } from "./markup.utils";

describe("splitMarkupSegments", () => {
  const textsOf = (value: string) =>
    splitMarkupSegments(value)
      .filter((segment) => !segment.isMarkup)
      .map((segment) => segment.text);

  it("should return nothing for an empty value", () => {
    expect(splitMarkupSegments("")).toEqual([]);
  });

  it("should return a single text segment for a value without markup", () => {
    expect(splitMarkupSegments("plain text")).toEqual([{ text: "plain text", isMarkup: false }]);
  });

  it("should split the tags from the text between them", () => {
    expect(splitMarkupSegments("Use <code>0</code> to hide")).toEqual([
      { text: "Use ", isMarkup: false },
      { text: "<code>", isMarkup: true },
      { text: "0", isMarkup: false },
      { text: "</code>", isMarkup: true },
      { text: " to hide", isMarkup: false }
    ]);
  });

  it("should treat character entities as markup", () => {
    expect(textsOf("key/&lt;regexp&gt;/")).toEqual(["key/", "regexp", "/"]);
    expect(textsOf("it&#39;s")).toEqual(["it", "s"]);
  });

  it("should keep a quoted attribute value containing a '>' inside the tag", () => {
    expect(textsOf('See <a title="a > b">docs</a>')).toEqual(["See ", "docs"]);
  });

  it("should leave a '<' that starts no tag in the text", () => {
    expect(textsOf("a < b and c > d")).toEqual(["a < b and c > d"]);
  });
});
