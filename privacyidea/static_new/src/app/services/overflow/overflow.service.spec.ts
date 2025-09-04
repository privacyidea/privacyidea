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
import { TestBed } from "@angular/core/testing";
import { OverflowService } from "./overflow.service";

describe("OverflowService (DOM logic)", () => {
  let service: OverflowService;
  let querySelectorSpy: jest.SpyInstance;
  let getComputedSpy: jest.SpyInstance;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({});
    service = TestBed.inject(OverflowService);
  });

  afterEach(() => {
    querySelectorSpy?.mockRestore();
    getComputedSpy?.mockRestore();
  });

  it("isWidthOverflowing → true when clientWidth below threshold", () => {
    const selector = { clientWidth: 100 } as HTMLElement;
    querySelectorSpy = jest.spyOn(document, "querySelector").mockReturnValue(selector as any);

    expect(service.isWidthOverflowing("#selector", 150)).toBe(true);
    expect(service.isWidthOverflowing("#selector", 80)).toBe(false);
  });

  it("isWidthOverflowing returns false if element not found", () => {
    querySelectorSpy = jest.spyOn(document, "querySelector").mockReturnValue(null);
    expect(service.isWidthOverflowing("#missing", 100)).toBe(false);
  });

  it("isHeightOverflowing with numeric threshold", () => {
    const el = { clientHeight: 120 } as HTMLElement;
    querySelectorSpy = jest.spyOn(document, "querySelector").mockReturnValue(el as any);

    expect(service.isHeightOverflowing({ selector: "#selector", threshold: 200 })).toBe(true);
    expect(service.isHeightOverflowing({ selector: "#selector", threshold: 100 })).toBe(false);
  });

  it("isHeightOverflowing with thresholdSelector (padding trimmed)", () => {
    const element = { clientHeight: 100 } as HTMLElement;
    const thresholdEl = { clientHeight: 200 } as HTMLElement;

    querySelectorSpy = jest
      .spyOn(document, "querySelector")
      .mockImplementation((sel: string) => (sel === "#target" ? element : thresholdEl));

    getComputedSpy = jest
      .spyOn(window, "getComputedStyle")
      .mockReturnValue({ paddingBottom: "20px" } as any);

    expect(
      service.isHeightOverflowing({
        selector: "#target",
        thresholdSelector: "#thr"
      })
    ).toBe(true);

    (element as any).clientHeight = 350;
    expect(
      service.isHeightOverflowing({
        selector: "#target",
        thresholdSelector: "#thr"
      })
    ).toBe(false);
  });

  it("isHeightOverflowing returns false if target element missing", () => {
    querySelectorSpy = jest.spyOn(document, "querySelector").mockReturnValue(null);
    expect(service.isHeightOverflowing({ selector: "#x" })).toBe(false);
  });

  it("getOverflowThreshold returns configured values", () => {
    expect(service.getOverflowThreshold()).toBe(1920);
  });
});
