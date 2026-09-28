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
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatPaginatorModule } from "@angular/material/paginator";
import { PaginatorCompactRangeDirective } from "./paginator-compact-range.directive";

interface FakeMutationObserver {
  cb: MutationCallback;
  observed: Element[];
  disconnect: jest.Mock;
}

interface FakeResizeObserver {
  cb: ResizeObserverCallback;
  observed: Element[];
  disconnect: jest.Mock;
}

@Component({
  standalone: true,
  imports: [MatPaginatorModule, MatFormFieldModule, MatInputModule, PaginatorCompactRangeDirective],
  template: `
    <div class="page-root">
      <div class="filter-paginator-container">
        <div class="filter-actions-group">
          <mat-form-field class="token-table-filter">
            <input matInput />
          </mat-form-field>
        </div>
        <mat-paginator
          appPaginatorCompactRange
          [length]="length"
          [pageIndex]="pageIndex"
          [pageSize]="pageSize"
          [pageSizeOptions]="[10, 20]"></mat-paginator>
      </div>
      <div class="table-scroll-region"></div>
    </div>
  `
})
class HostComponent {
  length = 10189;
  pageIndex = 0;
  pageSize = 10;
}

@Component({
  standalone: true,
  imports: [MatPaginatorModule, PaginatorCompactRangeDirective],
  template: `
    <div class="filter-paginator-container">
      <mat-paginator
        appPaginatorCompactRange
        [length]="10189"
        [pageIndex]="0"
        [pageSize]="10"
        [pageSizeOptions]="[10, 20]"></mat-paginator>
    </div>
  `
})
class HostWithoutScrollRegionComponent {}

// Fixed reference widths the gap is computed from: containerWidth - groupWidth - paginatorWidth.
// Only the group's width is varied per test to land on a desired gap; the other two stay constant.
const CONTAINER_WIDTH = 1000;
const PAGINATOR_WIDTH = 300;

describe("PaginatorCompactRangeDirective", () => {
  let fixture: ComponentFixture<HostComponent>;
  let mutationObservers: FakeMutationObserver[];
  let resizeObservers: FakeResizeObserver[];

  const rangeLabel = (): HTMLElement => fixture.nativeElement.querySelector(".mat-mdc-paginator-range-label");
  const scrollRegion = (): HTMLElement => fixture.nativeElement.querySelector(".table-scroll-region");
  const container = (): HTMLElement => fixture.nativeElement.querySelector(".filter-paginator-container");
  const group = (): HTMLElement => fixture.nativeElement.querySelector(".filter-actions-group");
  const paginatorHost = (): HTMLElement => fixture.nativeElement.querySelector("mat-paginator");

  // The directive creates exactly one MutationObserver: the class-attribute watcher on
  // .table-scroll-region. Genuine paginator data changes are picked up via ngDoCheck instead (see
  // the directive's own comment on why), so triggering that just means fixture.detectChanges().
  const triggerClassChange = () => mutationObservers[0].cb([], mutationObservers[0] as unknown as MutationObserver);

  // Angular Material's own form-field internals also use a ResizeObserver (for its outline notch),
  // so pick out the one this directive created by which element it actually observes.
  const ourResizeObserver = (): FakeResizeObserver =>
    resizeObservers.find((observer) => observer.observed[0] === container())!;
  const triggerResize = () => {
    const observer = ourResizeObserver();
    observer.cb([], observer as unknown as ResizeObserver);
  };

  // Sets up the three measured widths so that containerWidth - groupWidth - paginatorWidth equals
  // the given gap, holding the container and paginator widths fixed.
  const setGap = (gap: number) => {
    jest.spyOn(container(), "getBoundingClientRect").mockReturnValue({ width: CONTAINER_WIDTH } as DOMRect);
    jest.spyOn(paginatorHost(), "getBoundingClientRect").mockReturnValue({ width: PAGINATOR_WIDTH } as DOMRect);
    jest
      .spyOn(group(), "getBoundingClientRect")
      .mockReturnValue({ width: CONTAINER_WIDTH - PAGINATOR_WIDTH - gap } as DOMRect);
  };

  beforeEach(async () => {
    mutationObservers = [];
    resizeObservers = [];
    (globalThis.MutationObserver as unknown as jest.Mock).mockImplementation((cb: MutationCallback) => {
      const observer: FakeMutationObserver = { cb, observed: [], disconnect: jest.fn() };
      mutationObservers.push(observer);
      return {
        observe: (el: Element) => observer.observed.push(el),
        disconnect: observer.disconnect,
        takeRecords: () => []
      };
    });
    (globalThis.ResizeObserver as unknown as jest.Mock).mockImplementation((cb: ResizeObserverCallback) => {
      const observer: FakeResizeObserver = { cb, observed: [], disconnect: jest.fn() };
      resizeObservers.push(observer);
      return {
        observe: (el: Element) => observer.observed.push(el),
        unobserve: jest.fn(),
        disconnect: observer.disconnect
      };
    });

    await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();

    // ngAfterViewInit's own first apply() call measures against jsdom's real (unmocked)
    // getBoundingClientRect, which reports 0 width for everything and so latches compact mode on
    // straight away. Settle onto a wide-open gap before each test starts, so that latch clears and
    // tests start from full/unsqueezed.
    setGap(500);
    triggerResize();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("shows the full range label while not scrolled and the row has room", () => {
    expect(rangeLabel().textContent?.trim()).toBe("1 – 10 of 10189");
  });

  it("observes the scroll region's class and the container's size", () => {
    expect(mutationObservers).toHaveLength(1);
    expect(mutationObservers[0].observed[0]).toBe(scrollRegion());
    expect(ourResizeObserver().observed[0]).toBe(container());
  });

  it("picks up a genuine paginator data change on the next change-detection pass", () => {
    fixture.componentInstance.length = 3;
    fixture.detectChanges();
    fixture.detectChanges();

    expect(rangeLabel().textContent?.trim()).toBe("1 – 3 of 3");
  });

  it("collapses to just the range once the sibling scroll region is scrolled from the top", () => {
    scrollRegion().classList.add("scrolled-from-top");
    triggerClassChange();

    expect(rangeLabel().textContent?.trim()).toBe("1 – 10");
  });

  it("restores the full range label once scrolled back to the top", () => {
    scrollRegion().classList.add("scrolled-from-top");
    triggerClassChange();

    scrollRegion().classList.remove("scrolled-from-top");
    triggerClassChange();

    expect(rangeLabel().textContent?.trim()).toBe("1 – 10 of 10189");
  });

  it("does nothing when re-triggered with no actual change", () => {
    scrollRegion().classList.add("scrolled-from-top");
    triggerClassChange();
    expect(rangeLabel().textContent?.trim()).toBe("1 – 10");

    triggerClassChange();
    expect(rangeLabel().textContent?.trim()).toBe("1 – 10");
  });

  it("collapses to just the range once the row's gap runs out, even while not scrolled", () => {
    setGap(0);
    triggerResize();

    expect(rangeLabel().textContent?.trim()).toBe("1 – 10");
  });

  it("restores the full range label once there is comfortably enough gap again", () => {
    setGap(0);
    triggerResize();
    expect(rangeLabel().textContent?.trim()).toBe("1 – 10");

    // Past the release threshold (see the directive's own RELEASE_GAP_PX comment for why the gap
    // merely reaching zero again would not release it).
    setGap(130);
    triggerResize();

    expect(rangeLabel().textContent?.trim()).toBe("1 – 10 of 10189");
  });

  it("stays compact when the gap only reaches its bare engage threshold, short of the release threshold", () => {
    setGap(0);
    triggerResize();

    setGap(20);
    triggerResize();

    expect(rangeLabel().textContent?.trim()).toBe("1 – 10");
  });

  it("does not re-enter itself across repeated change-detection passes (regression: a measure-by-mutating design looped here)", () => {
    scrollRegion().classList.add("scrolled-from-top");
    triggerClassChange();
    expect(rangeLabel().textContent?.trim()).toBe("1 – 10");

    // Simulates Angular re-running change detection for unrelated reasons, exactly as a real app
    // does constantly - a version of apply() that mutated the label as part of measuring (rather
    // than only reading current widths) rewrote it every single time ngDoCheck ran, which is far
    // more often than any genuine data or layout change.
    for (let i = 0; i < 5; i++) {
      fixture.detectChanges();
    }

    expect(rangeLabel().textContent?.trim()).toBe("1 – 10");
  });

  it("disconnects all observers on destroy", () => {
    const resizeObserver = ourResizeObserver();
    fixture.destroy();

    expect(mutationObservers[0].disconnect).toHaveBeenCalled();
    expect(resizeObserver.disconnect).toHaveBeenCalled();
  });

  it("leaves the full range label alone when there is no sibling scroll region", async () => {
    await TestBed.resetTestingModule()
      .configureTestingModule({ imports: [HostWithoutScrollRegionComponent] })
      .compileComponents();
    const otherFixture = TestBed.createComponent(HostWithoutScrollRegionComponent);
    expect(() => otherFixture.detectChanges()).not.toThrow();

    const label = otherFixture.nativeElement.querySelector(".mat-mdc-paginator-range-label");
    expect(label.textContent?.trim()).toBe("1 – 10 of 10189");
  });
});
