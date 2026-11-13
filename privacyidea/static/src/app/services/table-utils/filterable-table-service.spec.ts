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
import { signal, WritableSignal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { DEBOUNCE_MS } from "@utils/debounce.utils";
import { FilterableTableService } from "./filterable-table-service";

class TestTableService extends FilterableTableService {
  readonly activeFilter: WritableSignal<FilterValue> = signal(new FilterValue());
  readonly apiFilterKeys = ["serial", "user", "type"];
  override readonly advancedApiFilterKeys = ["infokey"];
  override readonly hiddenApiFilterKeys = ["container_serial"];
  override readonly exactMatchKeys = new Set(["type"]);
  pageIndex = signal(0);
  pageSize = signal(10);
  sort = signal<Sort>({ active: "serial", direction: "asc" });
}

class PresenceTableService extends TestTableService {
  override readonly apiFilterKeys = ["serial", "user", "type", "tokenrealm"];
  override readonly hiddenApiFilterKeys = ["container_serial"];
  override readonly presenceKeys = new Set(["tokenrealm"]);
  override readonly keepEmptyKeys = new Set(["container_serial"]);
}

const inputEvent = (value: string) => ({ target: { value } }) as unknown as Event;

describe("FilterableTableService", () => {
  let service: TestTableService;

  beforeEach(() => {
    jest.useFakeTimers();
    service = new TestTableService();
  });

  afterEach(() => jest.useRealTimers());

  it("offers the api, the advanced and the hidden keywords", () => {
    expect(service.allFilterKeys()).toEqual(["serial", "user", "type", "infokey", "container_serial"]);
  });

  describe("filterParams", () => {
    it("builds the query parameters from the active filter", () => {
      service.setFilter(new FilterValue({ value: "serial: OATH user: alice" }));

      expect(service.filterParams()).toEqual({ serial: "*OATH*", user: "*alice*" });
    });

    it("does not wrap an exactly matched keyword in wildcards", () => {
      service.setFilter(new FilterValue({ value: "type: hotp" }));

      expect(service.filterParams()).toEqual({ type: "hotp" });
    });

    it("skips a keyword the backend does not know", () => {
      service.setFilter(new FilterValue({ value: "serial: OATH unknown: value" }));

      expect(service.filterParams()).toEqual({ serial: "*OATH*" });
    });

    it("keeps the same object when a new filter yields the same parameters", () => {
      service.setFilter(new FilterValue({ value: "serial: OATH" }));
      const params = service.filterParams();

      service.setFilter(new FilterValue({ value: "serial:   OATH" }));

      expect(service.filterParams()).toBe(params);
    });
  });

  describe("filterParams with keepEmptyKeys and presenceKeys", () => {
    let presence: PresenceTableService;
    const paramsFor = (value: string) => {
      presence.setFilter(new FilterValue({ value }));
      return presence.filterParams();
    };

    beforeEach(() => {
      presence = new PresenceTableService();
    });

    it("has no keepEmptyKeys and no presenceKeys by default", () => {
      expect(service.keepEmptyKeys.size).toBe(0);
      expect(service.presenceKeys.size).toBe(0);
    });

    it("sends an empty value of a keepEmptyKeys key as key=, bare or quoted", () => {
      expect(paramsFor("container_serial:")).toEqual({ container_serial: "" });
      expect(paramsFor("container_serial: \"\"")).toEqual({ container_serial: "" });
      expect(paramsFor("serial: abc container_serial:")).toEqual({ serial: "*abc*", container_serial: "" });
    });

    it("sends no parameter for a wildcard-only value of a keepEmptyKeys key", () => {
      expect(paramsFor("container_serial: *")).toEqual({});
    });

    it("sends key=* for a wildcard-only value of a presenceKeys key", () => {
      expect(paramsFor("tokenrealm: *")).toEqual({ tokenrealm: "*" });
      expect(paramsFor("tokenrealm: **")).toEqual({ tokenrealm: "*" });
    });

    it("sends key=* for a list that contains a wildcard-only entry", () => {
      expect(paramsFor("tokenrealm: *,realm1")).toEqual({ tokenrealm: "*" });
      expect(paramsFor("tokenrealm: realm1, **")).toEqual({ tokenrealm: "*" });
    });

    it("sends key= for a quoted empty value of a presenceKeys key", () => {
      expect(paramsFor("tokenrealm: \"\"")).toEqual({ tokenrealm: "" });
      expect(paramsFor("tokenrealm: \"\" serial: abc")).toEqual({ tokenrealm: "", serial: "*abc*" });
    });

    it("sends nothing for a bare presenceKeys key", () => {
      expect(paramsFor("tokenrealm:")).toEqual({});
      expect(paramsFor("tokenrealm: serial: abc")).toEqual({ serial: "*abc*" });
    });

    it("sends nothing for a presenceKeys list without entries", () => {
      expect(paramsFor("tokenrealm: ,")).toEqual({});
    });

    it("keeps a wildcard-only and an empty value meaning no filter for every other key", () => {
      expect(paramsFor("tokenrealm: * serial: * user: \"\" type: **")).toEqual({ tokenrealm: "*" });
    });

    it("leaves keys without a set to the usual rules", () => {
      expect(paramsFor("serial: OATH type: hotp")).toEqual({ serial: "*OATH*", type: "hotp" });
    });
  });

  describe("setFilter", () => {
    it("applies the filter at once", () => {
      service.setFilter(new FilterValue({ value: "serial: OATH" }));

      expect(service.activeFilter().value).toBe("serial: OATH");
      expect(service.filterDraft().value).toBe("serial: OATH");
    });
  });

  describe("updateFilter", () => {
    it("applies a filter computed from the current one", () => {
      service.setFilter(new FilterValue({ value: "serial: OATH" }));

      service.updateFilter((current) => current.addEntry("user", "alice"));

      expect(service.activeFilter().getValueOfKey("serial")).toBe("OATH");
      expect(service.activeFilter().getValueOfKey("user")).toBe("alice");
    });

    it("computes from what the user typed, not from the applied filter", () => {
      service.handleFilterInput(inputEvent("serial: OATH"));

      service.updateFilter((current) => current.addEntry("user", "alice"));

      expect(service.activeFilter().getValueOfKey("serial")).toBe("OATH");
      expect(service.activeFilter().getValueOfKey("user")).toBe("alice");
    });
  });

  describe("clearFilter", () => {
    it("clears what the user typed", () => {
      service.setFilter(new FilterValue({ value: "serial: OATH" }));

      service.clearFilter();

      expect(service.activeFilter().value).toBe("");
      expect(service.filterParams()).toEqual({});
    });

    it("keeps the hidden entries", () => {
      service.setFilter(new FilterValue({ value: "serial: OATH", hiddenValue: "container_serial: CONT0001" }));

      service.clearFilter();

      expect(service.activeFilter().hiddenValue).toBe("container_serial: CONT0001");
    });
  });

  describe("filterFromInput", () => {
    it("keeps the hidden entries of the active filter", () => {
      service.setFilter(new FilterValue({ hiddenValue: "container_serial: CONT0001" }));

      const filter = service.filterFromInput(inputEvent("serial: OATH"));

      expect(filter.value).toBe("serial: OATH");
      expect(filter.hiddenValue).toBe("container_serial: CONT0001");
    });
  });

  describe("handleFilterInput", () => {
    it("shows the typed value at once but applies it only after the delay", () => {
      service.handleFilterInput(inputEvent("serial: OATH"));

      expect(service.filterDraft().value).toBe("serial: OATH");
      expect(service.activeFilter().value).toBe("");

      jest.advanceTimersByTime(DEBOUNCE_MS);

      expect(service.activeFilter().value).toBe("serial: OATH");
      expect(service.filterParams()).toEqual({ serial: "*OATH*" });
    });

    it("applies only the last of several keystrokes", () => {
      service.handleFilterInput(inputEvent("serial: O"));
      service.handleFilterInput(inputEvent("serial: OA"));
      service.handleFilterInput(inputEvent("serial: OAT"));

      jest.advanceTimersByTime(DEBOUNCE_MS);

      expect(service.activeFilter().value).toBe("serial: OAT");
    });
  });

  describe("applyFilterInput", () => {
    it("applies the typed value at once", () => {
      service.applyFilterInput(inputEvent("serial: OATH"));

      expect(service.activeFilter().value).toBe("serial: OATH");
    });

    it("supersedes a keystroke that is still waiting", () => {
      service.handleFilterInput(inputEvent("serial: OAT"));
      service.applyFilterInput(inputEvent("serial: OATH"));

      jest.advanceTimersByTime(DEBOUNCE_MS);

      expect(service.activeFilter().value).toBe("serial: OATH");
    });
  });
});
