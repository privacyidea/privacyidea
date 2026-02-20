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

import { FilterOption, DummyFilterOption } from "./filter-option";
import { FilterValueGeneric } from "./filter-value-generic";

describe("FilterOption", () => {
  interface ComplexMock {
    id: number;
    details: {
      tags: string[];
      owner: { name: string; active: boolean };
    };
  }

  /**
   * Factory to create valid mock data without unsafe casting errors.
   */
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

  const mockFilterValue = {} as FilterValueGeneric<ComplexMock>;

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

    it("should verify matches() logic is preserved in clones", () => {
      const cloned = original.withValue("test");
      const valid = createMockItem({ details: { tags: ["security"], owner: { name: "a", active: true } } });
      const invalid = createMockItem({ details: { tags: [], owner: { name: "a", active: true } } });

      expect(cloned.matches(valid, mockFilterValue)).toBe(true);
      expect(cloned.matches(invalid, mockFilterValue)).toBe(false);
    });
  });

  describe("DummyFilterOption: Inheritance and Safety", () => {
    const dummy = new DummyFilterOption<ComplexMock>({ key: "freitext", value: "init" });

    it("should report as dummy and maintain correct prototype", () => {
      expect(dummy.isDummy).toBe(true);
      expect(dummy instanceof FilterOption).toBe(true);
      expect(dummy instanceof DummyFilterOption).toBe(true);
    });

    it("should force the key as the label for dummies", () => {
      expect(dummy.label).toBe("freitext");
    });

    it("should correctly handle withValue() while maintaining Dummy instance", () => {
      const next = dummy.withValue("updated-search");
      expect(next instanceof DummyFilterOption).toBe(true);
      expect(next.isDummy).toBe(true);
      expect(next.value).toBe("updated-search");
    });
  });

  describe("Edge Case Stress Tests", () => {
    it("should handle empty string as a valid distinct value from null", () => {
      const option = new FilterOption({ key: "k", label: "l", matches: () => true }).withValue("");
      expect(option.value).toBe("");
      expect(option.value).not.toBeNull();
    });

    it("should verify optional callback execution safety", () => {
      const toggleSpy = jest.fn();
      const iconSpy = jest.fn().mockReturnValue("test-icon");

      const option = new FilterOption({
        key: "k",
        label: "l",
        matches: () => true,
        toggle: toggleSpy,
        iconName: iconSpy
      });

      option.toggle?.(mockFilterValue);
      const icon = option.getIconName?.(mockFilterValue);

      expect(toggleSpy).toHaveBeenCalledWith(mockFilterValue);
      expect(iconSpy).toHaveBeenCalledWith(mockFilterValue);
      expect(icon).toBe("test-icon");
    });

    it("should handle multi-step nullification", () => {
      const f = new FilterOption({ key: "k", label: "l", matches: () => true })
        .withValue("val")
        .withValue(null)
        .withValue("val2")
        .withValue(null);

      expect(f.value).toBeNull();
    });

    it("should prevent cross-contamination of properties between instances", () => {
      const opt1 = new FilterOption({ key: "key1", label: "L1", matches: () => true });
      const opt2 = opt1.withValue("V1");

      expect(opt1.value).toBeNull();
      expect(opt2.value).toBe("V1");
      expect(opt1.key).toBe("key1");
      expect(opt2.key).toBe("key1");
    });
  });
});
