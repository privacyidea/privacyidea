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
import { createPaginatorIntl } from "./paginator-intl";

describe("createPaginatorIntl", () => {
  it("sets the localized static labels", () => {
    const intl = createPaginatorIntl();
    expect(intl.itemsPerPageLabel).toBeTruthy();
    expect(intl.nextPageLabel).toBeTruthy();
    expect(intl.previousPageLabel).toBeTruthy();
    expect(intl.firstPageLabel).toBeTruthy();
    expect(intl.lastPageLabel).toBeTruthy();
  });

  describe("getRangeLabel", () => {
    it("returns the empty-range label when length is 0", () => {
      const intl = createPaginatorIntl();
      expect(intl.getRangeLabel(0, 10, 0)).toContain("0");
    });

    it("returns the empty-range label when pageSize is 0", () => {
      const intl = createPaginatorIntl();
      expect(intl.getRangeLabel(0, 0, 5)).toContain("0");
    });

    it("computes the range for a full page", () => {
      const intl = createPaginatorIntl();
      const label = intl.getRangeLabel(0, 10, 25);
      expect(label).toContain("1");
      expect(label).toContain("10");
      expect(label).toContain("25");
    });

    it("clamps the end index to the total length on the last page", () => {
      const intl = createPaginatorIntl();
      const label = intl.getRangeLabel(2, 10, 25);
      expect(label).toContain("21");
      expect(label).toContain("25");
    });

    it("falls back to page-relative range when the page is beyond the last item", () => {
      const intl = createPaginatorIntl();
      const label = intl.getRangeLabel(5, 10, 25);
      expect(label).toContain("51");
      expect(label).toContain("60");
    });
  });
});
