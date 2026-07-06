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
import { ScrollEdgesDirective } from "./scroll-edges.directive";

interface EdgeEntry {
  isIntersecting: boolean;
}
type EdgeCallback = (entries: EdgeEntry[]) => void;

interface FakeObserver {
  cb: EdgeCallback;
  options: IntersectionObserverInit;
  observed: Element[];
  disconnect: jest.Mock;
}

@Component({
  standalone: true,
  imports: [ScrollEdgesDirective],
  template: `
    <div
      #region
      class="table-scroll-region"
      appScrollEdges>
      <div class="content">content</div>
    </div>
  `
})
class HostComponent {
  @ViewChild("region") region!: { nativeElement: HTMLElement };
}

describe("ScrollEdgesDirective", () => {
  let fixture: ComponentFixture<HostComponent>;
  let observers: FakeObserver[];

  beforeEach(async () => {
    observers = [];
    (globalThis.IntersectionObserver as unknown as jest.Mock).mockImplementation(
      (cb: EdgeCallback, options: IntersectionObserverInit) => {
        const observer: FakeObserver = { cb, options, observed: [], disconnect: jest.fn() };
        observers.push(observer);
        return {
          observe: (el: Element) => observer.observed.push(el),
          unobserve: jest.fn(),
          disconnect: observer.disconnect
        };
      }
    );

    await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
  });

  function regionEl(): HTMLElement {
    return fixture.componentInstance.region.nativeElement;
  }

  it("inserts a zero-height sentinel at the top and bottom of the scroll region", () => {
    const first = regionEl().firstElementChild as HTMLElement;
    const last = regionEl().lastElementChild as HTMLElement;
    expect(first.tagName.toLowerCase()).toBe("div");
    expect(first.style.height).toBe("0px");
    expect(last.style.height).toBe("0px");
    expect(first).not.toBe(last);
  });

  it("observes both sentinels with the region itself as the root", () => {
    expect(observers).toHaveLength(2);
    expect(observers[0].options.root).toBe(regionEl());
    expect(observers[1].options.root).toBe(regionEl());
    expect(observers[0].observed[0]).toBe(regionEl().firstElementChild);
    expect(observers[1].observed[0]).toBe(regionEl().lastElementChild);
  });

  it("toggles scrolled-from-top when the top sentinel leaves and re-enters view", () => {
    observers[0].cb([{ isIntersecting: false }]);
    expect(regionEl().classList.contains("scrolled-from-top")).toBe(true);
    observers[0].cb([{ isIntersecting: true }]);
    expect(regionEl().classList.contains("scrolled-from-top")).toBe(false);
  });

  it("toggles more-below based on the bottom sentinel visibility", () => {
    observers[1].cb([{ isIntersecting: false }]);
    expect(regionEl().classList.contains("more-below")).toBe(true);
    observers[1].cb([{ isIntersecting: true }]);
    expect(regionEl().classList.contains("more-below")).toBe(false);
  });

  it("disconnects both observers and removes both sentinels on destroy", () => {
    const first = regionEl().firstElementChild;
    const last = regionEl().lastElementChild;
    fixture.destroy();
    expect(observers[0].disconnect).toHaveBeenCalled();
    expect(observers[1].disconnect).toHaveBeenCalled();
    expect(first!.isConnected).toBe(false);
    expect(last!.isConnected).toBe(false);
  });
});
