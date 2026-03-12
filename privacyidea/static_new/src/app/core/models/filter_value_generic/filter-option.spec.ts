/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { FilterOption, DummyFilterOption, FilterActionType } from "./filter-option";
import { FilterValueGeneric } from "./filter-value-generic";

describe("FilterOption", () => {
  interface ComplexMock {
    id: number;
    details: {
      tags: string[];
      owner: { name: string; active: boolean };
    };
  }

  const createMockItem = (overrides: Partial<ComplexMock> = {}): ComplexMock => {
    return {
      id: 1,
      details: {
        tags: [],
        owner: { name: "root", active: true }
      },
      ...overrides
    };
  };

  const mockFilterValue = {
    hasKey: jest.fn()
  } as unknown as FilterValueGeneric<ComplexMock>;

  describe("Structural and Type Integrity", () => {
    it("should initialize all fields correctly via constructor", () => {
      const matches = (item: ComplexMock) => item.id > 0;
      const option = new FilterOption<ComplexMock>({
        key: "id",
        label: "ID Filter",
        value: "100",
        hint: "Numeric ID",
        matches
      });

      expect(option.key).toBe("id");
      expect(option.value).toBe("100");
      expect(option.label).toBe("ID Filter");
      expect(option.hint).toBe("Numeric ID");
      expect(option.matches).toBe(matches);
    });

    it("should strictly map null if value is not provided", () => {
      const option = new FilterOption({ key: "k", label: "l", matches: () => true });
      expect(option.value).toBeNull();
    });
  });

  describe("Immutability (The withValue method)", () => {
    const original = new FilterOption<ComplexMock>({
      key: "details.tags",
      label: "TagSearch",
      matches: (item) => item.details.tags.length > 0
    });

    it("should ensure reference inequality on every update", () => {
      const first = original.withValue("tag1");
      const second = first.withValue("tag2");

      expect(first).not.toBe(original);
      expect(second).not.toBe(first);
    });

    it("should propagate all metadata during value updates", () => {
      const hintOption = new FilterOption<ComplexMock>({
        key: "x",
        label: "y",
        hint: "persistent-hint",
        matches: () => true
      });
      const updated = hintOption.withValue("new-data");

      expect(updated.hint).toBe("persistent-hint");
      expect(updated.label).toBe("y");
      expect(updated.key).toBe("x");
    });
  });

  describe("Action Logic (getActionType)", () => {
    it("should use default logic: 'add' if key is missing", () => {
      (mockFilterValue.hasKey as jest.Mock).mockReturnValue(false);
      const option = new FilterOption({ key: "testKey", label: "L", matches: () => true });

      expect(option.getActionType!(mockFilterValue)).toBe("add");
    });

    it("should use default logic: 'remove' if key is present", () => {
      (mockFilterValue.hasKey as jest.Mock).mockReturnValue(true);
      const option = new FilterOption({ key: "testKey", label: "L", matches: () => true });

      expect(option.getActionType!(mockFilterValue)).toBe("remove");
    });

    it("should allow overriding getActionType via constructor", () => {
      const customAction: FilterActionType = "change";
      const option = new FilterOption({
        key: "k",
        label: "l",
        matches: () => true,
        getActionType: () => customAction
      });

      expect(option.getActionType!(mockFilterValue)).toBe("change");
    });

    it("should preserve custom getActionType in withValue() clones", () => {
      const option = new FilterOption({
        key: "k",
        label: "l",
        matches: () => true,
        getActionType: () => "change"
      });
      const cloned = option.withValue("new");

      expect(cloned.getActionType!(mockFilterValue)).toBe("change");
    });
  });

  describe("DummyFilterOption: Inheritance and Safety", () => {
    const dummy = new DummyFilterOption<ComplexMock>({ key: "freitext", value: "init" });

    it("should report as dummy and maintain correct prototype", () => {
      expect(dummy.isDummy).toBe(true);
      expect(dummy instanceof FilterOption).toBe(true);
      expect(dummy instanceof DummyFilterOption).toBe(true);
    });

    it("should correctly handle withValue() while maintaining Dummy instance", () => {
      const next = dummy.withValue("updated-search");
      expect(next instanceof DummyFilterOption).toBe(true);
      expect(next.isDummy).toBe(true);
      expect(next.value).toBe("updated-search");
    });
  });

  describe("Edge Case Stress Tests", () => {
    it("should verify optional toggle execution safety", () => {
      const toggleSpy = jest.fn();
      const option = new FilterOption({
        key: "k",
        label: "l",
        matches: () => true,
        toggle: toggleSpy
      });

      option.toggle?.(mockFilterValue);
      expect(toggleSpy).toHaveBeenCalledWith(mockFilterValue);
    });

    it("should handle multi-step nullification", () => {
      const f = new FilterOption({ key: "k", label: "l", matches: () => true })
        .withValue("val")
        .withValue(null)
        .withValue("val2")
        .withValue(null);

      expect(f.value).toBeNull();
    });
  });
});
