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
import { ScrollFocusableDirective } from "./scroll-focusable.directive";

@Component({
  standalone: true,
  imports: [ScrollFocusableDirective],
  template: `<div appScrollFocusable></div>`
})
class HostComponent {}

describe("ScrollFocusableDirective", () => {
  let fixture: ComponentFixture<HostComponent>;
  let host: HTMLElement;
  let resizeCallback: () => void;
  const disconnect = jest.fn();

  const setSize = (scroll: { height: number; width: number }, client: { height: number; width: number }) => {
    Object.defineProperty(host, "scrollHeight", { configurable: true, value: scroll.height });
    Object.defineProperty(host, "scrollWidth", { configurable: true, value: scroll.width });
    Object.defineProperty(host, "clientHeight", { configurable: true, value: client.height });
    Object.defineProperty(host, "clientWidth", { configurable: true, value: client.width });
    resizeCallback();
  };

  beforeEach(() => {
    class FakeResizeObserver {
      constructor(callback: () => void) {
        resizeCallback = callback;
      }
      observe = jest.fn();
      disconnect = disconnect;
    }
    (globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = FakeResizeObserver;

    fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
    host = fixture.nativeElement.querySelector("div");
  });

  it("is not a tab stop while its content fits", () => {
    setSize({ height: 100, width: 100 }, { height: 100, width: 100 });

    expect(host.hasAttribute("tabindex")).toBe(false);
  });

  it("becomes a tab stop once its content overflows vertically", () => {
    setSize({ height: 300, width: 100 }, { height: 100, width: 100 });

    expect(host.getAttribute("tabindex")).toBe("0");
  });

  it("becomes a tab stop once its content overflows horizontally", () => {
    setSize({ height: 100, width: 300 }, { height: 100, width: 100 });

    expect(host.getAttribute("tabindex")).toBe("0");
  });

  it("drops out of the tab order when the content fits again", () => {
    setSize({ height: 300, width: 100 }, { height: 100, width: 100 });
    setSize({ height: 100, width: 100 }, { height: 100, width: 100 });

    expect(host.hasAttribute("tabindex")).toBe(false);
  });

  it("stops observing on destroy", () => {
    fixture.destroy();

    expect(disconnect).toHaveBeenCalled();
  });
});
