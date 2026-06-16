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
import { Component, ViewChild } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { StickyHeaderDirective } from "./sticky-header.directive";

type ObserverCallback = (
  entries: { boundingClientRect: { top: number }; rootBounds: { top: number } | null }[]
) => void;

@Component({
  standalone: true,
  imports: [StickyHeaderDirective],
  template: `
    <div
      #scrollContainer
      class="scroll-container">
      <h3>Title</h3>
      <div
        #header
        class="sticky-header"
        [appStickyHeader]="scrollContainer">
        Header
      </div>
      <div class="content">content</div>
    </div>
  `
})
class HostComponent {
  @ViewChild("header") header!: { nativeElement: HTMLElement };
  @ViewChild("scrollContainer") scrollContainer!: { nativeElement: HTMLElement };
}

describe("StickyHeaderDirective", () => {
  let fixture: ComponentFixture<HostComponent>;
  let observerCallback: ObserverCallback;
  let observeSpy: jest.Mock;
  let disconnectSpy: jest.Mock;
  let observerOptions: IntersectionObserverInit;

  beforeEach(async () => {
    observeSpy = jest.fn();
    disconnectSpy = jest.fn();
    (globalThis.IntersectionObserver as unknown as jest.Mock).mockImplementation(
      (cb: ObserverCallback, options: IntersectionObserverInit) => {
        observerCallback = cb;
        observerOptions = options;
        return { observe: observeSpy, unobserve: jest.fn(), disconnect: disconnectSpy };
      }
    );

    await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
  });

  function headerEl(): HTMLElement {
    return fixture.componentInstance.header.nativeElement;
  }

  it("inserts a sentinel right before the host header", () => {
    const sentinel = headerEl().previousElementSibling;
    expect(sentinel).not.toBeNull();
    expect(sentinel!.tagName.toLowerCase()).toBe("div");
    expect(sentinel!.textContent).toBe("");
  });

  it("observes the sentinel with the scroll container as the observer root", () => {
    expect(observerOptions.root).toBe(fixture.componentInstance.scrollContainer.nativeElement);
    expect(observerOptions.threshold).toEqual([0, 1]);
    expect(observeSpy).toHaveBeenCalledWith(headerEl().previousElementSibling);
  });

  it("adds is-sticky when the sentinel scrolls above the root top", () => {
    observerCallback([{ boundingClientRect: { top: -10 }, rootBounds: { top: 0 } }]);
    expect(headerEl().classList.contains("is-sticky")).toBe(true);
  });

  it("removes is-sticky when the sentinel is back within the root", () => {
    observerCallback([{ boundingClientRect: { top: -10 }, rootBounds: { top: 0 } }]);
    observerCallback([{ boundingClientRect: { top: 20 }, rootBounds: { top: 0 } }]);
    expect(headerEl().classList.contains("is-sticky")).toBe(false);
  });

  it("ignores entries without rootBounds", () => {
    observerCallback([{ boundingClientRect: { top: -10 }, rootBounds: null }]);
    expect(headerEl().classList.contains("is-sticky")).toBe(false);
  });

  it("disconnects the observer and removes the sentinel on destroy", () => {
    const sentinel = headerEl().previousElementSibling;
    fixture.destroy();
    expect(disconnectSpy).toHaveBeenCalled();
    expect(sentinel!.isConnected).toBe(false);
  });
});
