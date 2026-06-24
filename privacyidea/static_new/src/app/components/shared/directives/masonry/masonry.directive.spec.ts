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
import { Component } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MasonryDirective } from "./masonry.directive";

class MockResizeObserver {
  static instances: MockResizeObserver[] = [];
  observe = jest.fn();
  unobserve = jest.fn();
  disconnect = jest.fn();
  constructor(public callback: ResizeObserverCallback) {
    MockResizeObserver.instances.push(this);
  }
}

interface GlobalWithResizeObserver {
  ResizeObserver?: typeof ResizeObserver;
}
interface WindowWithRaf {
  requestAnimationFrame?: typeof window.requestAnimationFrame;
}

@Component({
  standalone: true,
  imports: [MasonryDirective],
  template: `
    <div
      appMasonry
      [columnWidthRem]="10">
      <div class="item">a</div>
      <span style="display: contents">
        <div class="item">b</div>
      </span>
      <div class="item">c</div>
    </div>
  `
})
class HostComponent {}

@Component({
  standalone: true,
  imports: [MasonryDirective],
  template: `
    <div
      appMasonry
      [columns]="3"
      [columnWidthRem]="10">
      <div class="item">a</div>
      <div class="item">b</div>
      <div class="item">c</div>
    </div>
  `
})
class FixedColumnsHostComponent {}

@Component({
  standalone: true,
  imports: [MasonryDirective],
  template: `
    <div
      appMasonry
      [columns]="6"
      [columnWidthRem]="30">
      <div class="item">a</div>
      <div class="item">b</div>
      <div class="item">c</div>
    </div>
  `
})
class ClampedColumnsHostComponent {}

describe("MasonryDirective", () => {
  let fixture: ComponentFixture<HostComponent>;
  let rafSpy: jest.SpyInstance;
  let originalResizeObserver: typeof ResizeObserver | undefined;
  let clientWidthDescriptor: PropertyDescriptor | undefined;
  let offsetHeightDescriptor: PropertyDescriptor | undefined;

  beforeEach(async () => {
    MockResizeObserver.instances = [];
    originalResizeObserver = (globalThis as GlobalWithResizeObserver).ResizeObserver;
    (globalThis as GlobalWithResizeObserver).ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;

    clientWidthDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "clientWidth");
    offsetHeightDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetHeight");
    Object.defineProperty(HTMLElement.prototype, "clientWidth", { configurable: true, get: () => 1000 });
    Object.defineProperty(HTMLElement.prototype, "offsetHeight", { configurable: true, get: () => 50 });

    // Run the scheduled layout synchronously so we exercise layout() within the test.
    rafSpy = jest.spyOn(window, "requestAnimationFrame").mockImplementation((cb: FrameRequestCallback) => {
      cb(0);
      return 1;
    });

    await TestBed.configureTestingModule({
      imports: [HostComponent, FixedColumnsHostComponent, ClampedColumnsHostComponent]
    }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
  });

  afterEach(() => {
    rafSpy.mockRestore();
    (globalThis as GlobalWithResizeObserver).ResizeObserver = originalResizeObserver;
    if (clientWidthDescriptor) {
      Object.defineProperty(HTMLElement.prototype, "clientWidth", clientWidthDescriptor);
    }
    if (offsetHeightDescriptor) {
      Object.defineProperty(HTMLElement.prototype, "offsetHeight", offsetHeightDescriptor);
    }
  });

  it("creates the host and lays out absolutely positioned items across multiple columns", () => {
    fixture.detectChanges();

    const host = fixture.nativeElement.querySelector("[appMasonry]") as HTMLElement;
    expect(host.style.position).toBe("relative");
    expect(parseFloat(host.style.height)).toBeGreaterThan(0);

    const items = Array.from(host.querySelectorAll(".item")) as HTMLElement[];
    expect(items.length).toBe(3);
    items.forEach((item) => {
      expect(item.style.position).toBe("absolute");
      expect(item.style.width).toContain("px");
    });
    // With a 1000px container and a 10rem column width, more than one column is used.
    const lefts = new Set(items.map((item) => item.style.left));
    expect(lefts.size).toBeGreaterThan(1);
  });

  it("observes the host and its (display: contents flattened) children via ResizeObserver", () => {
    fixture.detectChanges();

    const observer = MockResizeObserver.instances[0];
    expect(observer).toBeDefined();
    // host + 3 flattened item elements
    expect(observer.observe).toHaveBeenCalled();
  });

  it("disconnects observers and cancels the pending frame on destroy", () => {
    fixture.detectChanges();
    const observer = MockResizeObserver.instances[0];
    const cancelSpy = jest.spyOn(window, "cancelAnimationFrame");

    fixture.destroy();

    expect(observer.disconnect).toHaveBeenCalled();
    cancelSpy.mockRestore();
  });

  it("uses up to [columns] columns when they fit the available width", () => {
    // 1000px container, 10rem (160px) min column width → 5 would fit, capped to 3.
    const fx = TestBed.createComponent(FixedColumnsHostComponent);
    fx.detectChanges();

    const host = fx.nativeElement.querySelector("[appMasonry]") as HTMLElement;
    const items = Array.from(host.querySelectorAll(".item")) as HTMLElement[];
    const lefts = new Set(items.map((item) => item.style.left));
    expect(lefts.size).toBe(3);
  });

  it("reduces below [columns] when columns would be narrower than columnWidthRem (e.g. under zoom)", () => {
    // 1000px container, 30rem (480px) min column width → only 2 columns fit, so
    // the requested 6 is clamped to 2 instead of forcing 6 overlapping columns.
    const fx = TestBed.createComponent(ClampedColumnsHostComponent);
    fx.detectChanges();

    const host = fx.nativeElement.querySelector("[appMasonry]") as HTMLElement;
    const items = Array.from(host.querySelectorAll(".item")) as HTMLElement[];
    const lefts = new Set(items.map((item) => item.style.left));
    expect(lefts.size).toBe(2);
  });

  it("falls back to a synchronous layout when requestAnimationFrame is unavailable", () => {
    rafSpy.mockRestore();
    const originalRaf = window.requestAnimationFrame;
    (window as WindowWithRaf).requestAnimationFrame = undefined;

    expect(() => fixture.detectChanges()).not.toThrow();
    const host = fixture.nativeElement.querySelector("[appMasonry]") as HTMLElement;
    expect(host.style.position).toBe("relative");

    (window as WindowWithRaf).requestAnimationFrame = originalRaf;
  });
});
