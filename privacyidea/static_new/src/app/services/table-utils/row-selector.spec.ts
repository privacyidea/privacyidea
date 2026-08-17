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
import { computed, signal, WritableSignal } from "@angular/core";
import { RowSelector } from "./row-selector";

interface Server {
  identifier: string;
  port: number;
}

const serversOf = (...identifiers: string[]): Server[] =>
  identifiers.map((identifier, index) => ({ identifier, port: 25 + index }));

describe("RowSelector", () => {
  let rows: WritableSignal<Server[]>;
  let selector: RowSelector<Server>;

  beforeEach(() => {
    rows = signal(serversOf("a", "b", "c"));
    selector = new RowSelector<Server>({
      keyGetter: (server) => server.identifier,
      visibleRows: rows
    });
  });

  describe("initial state", () => {
    it("starts with nothing selected", () => {
      expect(selector.selectedRows()).toEqual([]);
      expect(selector.selectedCount()).toBe(0);
      expect(selector.hasSelection()).toBe(false);
      expect(selector.allRowsSelected()).toBe(false);
      expect(selector.someRowsSelected()).toBe(false);
    });

    it("exposes the rows it was given", () => {
      expect(selector.visibleRows()).toEqual(rows());
      expect(selector.hasVisibleRows()).toBe(true);
    });
  });

  describe("single rows", () => {
    it("selects and deselects a row", () => {
      const [a] = rows();

      selector.selectRow(a);
      expect(selector.isRowSelected(a)).toBe(true);
      expect(selector.selectedRows()).toEqual([a]);

      selector.deselectRow(a);
      expect(selector.isRowSelected(a)).toBe(false);
      expect(selector.selectedRows()).toEqual([]);
    });

    it("selecting the same row twice keeps a single entry", () => {
      const [a] = rows();

      selector.selectRow(a);
      selector.selectRow(a);

      expect(selector.selectedCount()).toBe(1);
    });

    it("deselecting an unselected row is a no-op", () => {
      const [a, b] = rows();
      selector.selectRow(a);

      selector.deselectRow(b);

      expect(selector.selectedRows()).toEqual([a]);
    });

    it("setRowSelected switches on the flag", () => {
      const [a] = rows();

      selector.setRowSelected(a, true);
      expect(selector.isRowSelected(a)).toBe(true);

      selector.setRowSelected(a, false);
      expect(selector.isRowSelected(a)).toBe(false);
    });

    it("returns the selected rows in the order the table shows them", () => {
      const [a, b, c] = rows();

      selector.selectRow(c);
      selector.selectRow(a);
      selector.selectRow(b);

      expect(selector.selectedRows()).toEqual([a, b, c]);
    });
  });

  describe("select all", () => {
    it("selects every visible row", () => {
      selector.selectAllRows();

      expect(selector.selectedCount()).toBe(3);
      expect(selector.allRowsSelected()).toBe(true);
      expect(selector.someRowsSelected()).toBe(false);
    });

    it("deselects every row", () => {
      selector.selectAllRows();

      selector.deselectAllRows();

      expect(selector.hasSelection()).toBe(false);
      expect(selector.allRowsSelected()).toBe(false);
    });

    it("never selects rows outside the visible ones", () => {
      const visible = computed(() => rows().slice(0, 2));
      const scoped = new RowSelector<Server>({
        keyGetter: (server) => server.identifier,
        visibleRows: visible
      });

      scoped.selectAllRows();

      expect(scoped.selectedRows().map((server) => server.identifier)).toEqual(["a", "b"]);
      expect(scoped.allRowsSelected()).toBe(true);
    });
  });

  describe("indeterminate state", () => {
    it("reports a partial selection", () => {
      selector.selectRow(rows()[0]);

      expect(selector.someRowsSelected()).toBe(true);
      expect(selector.allRowsSelected()).toBe(false);
    });

    it("reports neither state when everything is selected", () => {
      selector.selectAllRows();

      expect(selector.someRowsSelected()).toBe(false);
      expect(selector.allRowsSelected()).toBe(true);
    });
  });

  describe("empty table", () => {
    beforeEach(() => rows.set([]));

    it("is not all-selected", () => {
      expect(selector.allRowsSelected()).toBe(false);
      expect(selector.hasVisibleRows()).toBe(false);
    });

    it("stays empty when select-all is triggered", () => {
      selector.selectAllRows();

      expect(selector.selectedRows()).toEqual([]);
      expect(selector.allRowsSelected()).toBe(false);
    });
  });

  describe("when the visible rows change", () => {
    it("drops rows that left the view", () => {
      selector.selectAllRows();

      rows.set(serversOf("a"));

      expect(selector.selectedRows().map((server) => server.identifier)).toEqual(["a"]);
    });

    it("clears the selection when no row survives", () => {
      selector.selectAllRows();

      rows.set(serversOf("x", "y"));

      expect(selector.hasSelection()).toBe(false);
    });

    it("keeps the selection when the same data is reloaded", () => {
      selector.selectRow(rows()[0]);

      rows.set(serversOf("a", "b", "c"));

      expect(selector.selectedRows().map((server) => server.identifier)).toEqual(["a"]);
    });

    it("identifies rows by key, not by object reference", () => {
      selector.selectRow(rows()[1]);
      const reloaded = serversOf("a", "b", "c");

      rows.set(reloaded);

      expect(selector.selectedRows()[0]).toBe(reloaded[1]);
    });

    it("does not select rows that appear later", () => {
      selector.selectAllRows();

      rows.set(serversOf("a", "b", "c", "d"));

      expect(selector.allRowsSelected()).toBe(false);
      expect(selector.selectedRows().map((server) => server.identifier)).toEqual(["a", "b", "c"]);
    });

    it("holds no row that is not visible, across a sequence of changes", () => {
      const invariantHolds = () => {
        const visible = new Set(selector.visibleRows().map((server) => server.identifier));
        return selector.selectedRows().every((server) => visible.has(server.identifier));
      };

      for (const step of [
        () => selector.selectAllRows(),
        () => rows.set(serversOf("b", "c", "d")),
        () => selector.selectAllRows(),
        () => rows.set(serversOf("d")),
        () => rows.set([]),
        () => rows.set(serversOf("a", "b")),
        () => selector.selectRow(rows()[0])
      ]) {
        step();
        expect(invariantHolds()).toBe(true);
      }
    });
  });

  describe("key getter", () => {
    it("supports a composite key", () => {
      const composite = new RowSelector<Server>({
        keyGetter: (server) => `${server.identifier}:${server.port}`,
        visibleRows: signal([
          { identifier: "a", port: 25 },
          { identifier: "a", port: 587 }
        ])
      });

      composite.selectRow(composite.visibleRows()[0]);

      expect(composite.selectedCount()).toBe(1);
      expect(composite.someRowsSelected()).toBe(true);
    });
  });
});
