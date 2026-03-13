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

import { FilterValueGeneric } from "./filter-value-generic";
import { FilterOption } from "./filter-option";

describe("FilterValueGeneric", () => {
  interface PolicyMock {
    name: string;
    scope: string;
    priority: number;
    active: boolean;
    realm: string;
    tags: string[];
    description: string;
    "api-key": string; // Added for hyphen testing
  }

  const createMockOption = (key: string): FilterOption<PolicyMock> => {
    return new FilterOption<PolicyMock>({
      key,
      label: `Label ${key}`,
      matches: (item, f) => {
        const val = f.getFilterOfKey(key);
        if (!val) return true;
        if (key === "active") return item.active.toString() === val;
        if (key === "priority") return item.priority.toString() === val;
        return (item as any)[key]?.toString().toLowerCase().includes(val.toLowerCase());
      }
    });
  };

  let filter: FilterValueGeneric<PolicyMock>;

  beforeEach(() => {
    filter = new FilterValueGeneric<PolicyMock>({
      availableFilters: [
        createMockOption("name"),
        createMockOption("scope"),
        createMockOption("active"),
        createMockOption("priority"),
        createMockOption("realm"),
        createMockOption("tags"),
        createMockOption("description"),
        createMockOption("api-key")
      ]
    });
  });

  describe("1. Initialization & State Integrity", () => {
    it("should initialize with empty maps and correct boolean states", () => {
      expect(filter.isEmpty).toBe(true);
      expect(filter.isNotEmpty).toBe(false);
      expect(filter.hiddenIsEmpty).toBe(true);
      expect(filter.filterMap.size).toBe(0);
    });

    it("should correctly build the availableFilters map from an array", () => {
      expect(filter.availableFilters.has("name")).toBe(true);
      expect(filter.availableFilters.size).toBe(8);
    });

    it("should throw error when adding a hidden key that is not in availableFilters", () => {
      expect(() => filter.addHiddenKey("unknown_key")).toThrow();
    });
  });

  describe("2. Immutability & Reference Stability", () => {
    it("should return a new instance and not mutate on addKey", () => {
      const next = filter.addKey("name");
      expect(next).not.toBe(filter);
      expect(filter.isEmpty).toBe(true);
    });

    it("should maintain separate references for sequential value updates", () => {
      const f1 = filter.setValueOfKey("name", "a");
      const f2 = f1.setValueOfKey("name", "b");
      expect(f1.getFilterOfKey("name")).toBe("a");
      expect(f2.getFilterOfKey("name")).toBe("b");
      expect(f1).not.toBe(f2);
    });

    it("should return the same instance if removing a non-existent key", () => {
      const instance = filter.addKey("name");
      expect(instance.removeKey("ghost")).toBe(instance);
    });
  });

  describe("3. Advanced Parsing (Regex & String Resilience)", () => {
    it("should parse standard colon-separated pairs", () => {
      const res = filter.setByString("scope:admin active:true");
      expect(res.getFilterOfKey("scope")).toBe("admin");
      expect(res.getFilterOfKey("active")).toBe("true");
    });

    it("should support hyphens in keys (RE_KEY fix verification)", () => {
      const res = filter.setByString("api-key: secret-token-123");
      expect(res.getFilterOfKey("api-key")).toBe("secret-token-123");
    });

    it("should handle multi-word values with double quotes (lowercase output)", () => {
      const res = filter.setByString('name:"Strict Security Policy" realm:internal');
      expect(res.getFilterOfKey("name")).toBe("strict security policy");
      expect(res.getFilterOfKey("realm")).toBe("internal");
    });

    it("should correctly ignore leading/trailing whitespace around colons", () => {
      const res = filter.setByString("name :  value  ");
      expect(res.getFilterOfKey("name")).toBe("value");
    });

    it("should handle values that look like keys but aren't (colons in values)", () => {
      const res = filter.setByString("name:scope:admin");
      expect(res.getFilterOfKey("name")).toBe("scope:admin");
    });

    it("should handle escaped quotes and backslashes", () => {
      const res = filter.setByString('name:"Policy \\"Beta\\"" realm:C:\\\\Windows');
      expect(res.getFilterOfKey("name")).toBe('policy "beta"');
      expect(res.getFilterOfKey("realm")).toBe("c:\\windows");
    });

    it("should handle keys without values (trailing colons)", () => {
      const res = filter.setByString("name: priority:10");
      expect(res.hasKey("name")).toBe(true);
      expect(res.getFilterOfKey("name")).toBe("");
    });

    it("should treat standalone words as Dummies with null values", () => {
      const res = filter.setByString("standalone search_term");
      expect(res.getFilterOfKey("standalone")).toBeNull();
      expect(res.getFilterOfKey("search_term")).toBeNull();
      expect(res.filterMap.get("standalone")).toBeDefined();
    });
  });

  describe("4. Filtering Logic & Item Processing", () => {
    const data: PolicyMock[] = [
      {
        name: "P1",
        scope: "admin",
        priority: 1,
        active: true,
        realm: "r1",
        tags: [],
        description: "",
        "api-key": "k1"
      },
      { name: "P2", scope: "user", priority: 2, active: true, realm: "r2", tags: [], description: "", "api-key": "k2" },
      {
        name: "P3",
        scope: "admin",
        priority: 1,
        active: false,
        realm: "r1",
        tags: [],
        description: "",
        "api-key": "k3"
      }
    ];

    it("should filter using AND logic for multiple active keys", () => {
      const f = filter.setValueOfKey("scope", "admin").setValueOfKey("active", "true");
      const result = f.filterItems(data);
      expect(result.length).toBe(1);
      expect(result[0].name).toBe("P1");
    });

    it("should handle empty item lists gracefully", () => {
      expect(filter.filterItems([])).toEqual([]);
      expect(filter.filterItems(null as any)).toEqual([]);
    });

    it("should ignore missing properties on items without throwing", () => {
      const broken = [{ name: "B" } as any as PolicyMock];
      const f = filter.setValueOfKey("scope", "admin");
      expect(() => f.filterItems(broken)).not.toThrow();
      expect(f.filterItems(broken).length).toBe(0);
    });
  });

  describe("5. Hidden Filter Interaction & Shadowing", () => {
    it("should prioritize public values over hidden ones in getValueOfKey", () => {
      const f = filter.setValueOfKey("name", "public").addHiddenKey("name").setValueOfHiddenKey("name", "hidden");
      expect(f.getFilterOfKey("name")).toBe("public");
    });

    it("should correctly filter based on hidden criteria", () => {
      const items = [
        { name: "A", active: true },
        { name: "B", active: false }
      ] as PolicyMock[];
      const f = filter.addHiddenKey("active").setValueOfHiddenKey("active", "true");
      const res = f.filterItems(items);
      expect(res.length).toBe(1);
      expect(res[0].active).toBe(true);
    });
  });

  describe("6. API String & Serialization", () => {
    it("should exclude unknown keys (dummies) from API string", () => {
      const f = filter.setValueOfKey("name", "v").addKey("ghost").setValueOfKey("ghost", "v");
      expect(f.apiFilterString).toBe("name: v");
    });

    it("should sanitize wildcards out of API strings", () => {
      const f = filter.setValueOfKey("name", "*").setValueOfKey("scope", "***");
      expect(f.apiFilterString).toBe("");
    });

    it("should combine hidden and public filters for API", () => {
      const f = filter.setValueOfKey("name", "p").addHiddenKey("active").setValueOfHiddenKey("active", "t");
      expect(f.apiFilterString).toContain("name: p");
      expect(f.apiFilterString).toContain("active: t");
    });
  });

  describe("7. Performance Benchmark (Scalability)", () => {
    it("should process 10,000 items in under 150ms", () => {
      const largeData = Array.from({ length: 10000 }, (_, i) => ({
        name: `P${i}`,
        scope: "admin",
        active: true
      })) as PolicyMock[];

      const f = filter.setValueOfKey("scope", "admin");
      const start = performance.now();
      f.filterItems(largeData);
      const end = performance.now();
      expect(end - start).toBeLessThan(150);
    });
  });

  describe("8. Fuzz & Stress Testing (Stability)", () => {
    it("should never throw an error for randomized input strings", () => {
      const chars = "abcdefg :\"'\\_";
      for (let i = 0; i < 50; i++) {
        const randomInput = Array.from({ length: 50 }, () =>
          chars.charAt(Math.floor(Math.random() * chars.length))
        ).join("");
        expect(() => filter.setByString(randomInput)).not.toThrow();
      }
    });

    it("should remain stable with malicious looking inputs", () => {
      const nightmare = 'key:"\'\\"":: : : :   key2: : : ';
      expect(() => filter.setByString(nightmare)).not.toThrow();
    });
  });

  describe("9. UI Helpers", () => {
    it("should generate correct rawValue for UI search bar", () => {
      const f = filter.setValueOfKey("name", "test").addKey("standalone");
      expect(f.rawValue).toBe("name: test standalone");
    });
  });
});
