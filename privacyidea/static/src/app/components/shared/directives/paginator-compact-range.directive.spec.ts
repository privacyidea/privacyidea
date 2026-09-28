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

describe("PaginatorCompactRangeDirective", () => {
  let fixture: ComponentFixture<HostComponent>;
  let mutationObservers: FakeMutationObserver[];

  const rangeLabel = (): HTMLElement => fixture.nativeElement.querySelector(".mat-mdc-paginator-range-label");
  const scrollRegion = (): HTMLElement => fixture.nativeElement.querySelector(".table-scroll-region");

  // The directive creates exactly one MutationObserver: the class-attribute watcher on
  // .table-scroll-region. Genuine paginator data changes are picked up via ngDoCheck instead (see
  // the directive's own comment on why), so triggering that just means fixture.detectChanges().
  const triggerClassChange = () => mutationObservers[0].cb([], mutationObservers[0] as unknown as MutationObserver);

  beforeEach(async () => {
    mutationObservers = [];
    (globalThis.MutationObserver as unknown as jest.Mock).mockImplementation((cb: MutationCallback) => {
      const observer: FakeMutationObserver = { cb, observed: [], disconnect: jest.fn() };
      mutationObservers.push(observer);
      return {
        observe: (el: Element) => observer.observed.push(el),
        disconnect: observer.disconnect,
        takeRecords: () => []
      };
    });

    await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("shows the full range label while not scrolled and the row has room", () => {
    expect(rangeLabel().textContent?.trim()).toBe("1 – 10 of 10189");
  });

  it("observes the scroll region's class", () => {
    expect(mutationObservers).toHaveLength(1);
    expect(mutationObservers[0].observed[0]).toBe(scrollRegion());
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

  it("disconnects its observer on destroy", () => {
    fixture.destroy();

    expect(mutationObservers[0].disconnect).toHaveBeenCalled();
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
