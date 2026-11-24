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
import { ScrollToTopDirective } from "./app-scroll-to-top.directive";

@Component({
  standalone: true,
  imports: [ScrollToTopDirective],
  template: `<div appScrollToTop></div>`
})
class HostComponent {}

describe("ScrollToTopDirective", () => {
  let fixture: ComponentFixture<HostComponent>;
  let host: HTMLElement;
  let button: HTMLButtonElement;

  const scrollTo = (top: number) => {
    host.scrollTop = top;
    host.dispatchEvent(new Event("scroll"));
  };

  beforeEach(() => {
    fixture = TestBed.configureTestingModule({ imports: [HostComponent] }).createComponent(HostComponent);
    fixture.detectChanges();
    host = fixture.nativeElement.querySelector("div");
    button = host.querySelector<HTMLButtonElement>(".scroll-to-top-fab")!;
    host.scrollTo = jest.fn() as unknown as typeof host.scrollTo;
  });

  it("shows the button once the page is scrolled and hides it at the top", () => {
    expect(button.style.display).toBe("none");
    scrollTo(500);
    expect(button.style.display).toBe("flex");
    scrollTo(0);
    expect(button.style.display).toBe("none");
  });

  it("keeps the button while it holds keyboard focus and hides it once focus leaves", () => {
    scrollTo(500);
    button.dispatchEvent(new Event("focus"));
    scrollTo(0);
    expect(button.style.display).toBe("flex");

    button.dispatchEvent(new Event("blur"));
    expect(button.style.display).toBe("none");
  });

  it("scrolls to the top and lets go of focus when clicked", () => {
    scrollTo(500);
    const blur = jest.spyOn(button, "blur");
    button.click();
    expect(host.scrollTo).toHaveBeenCalledWith({ top: 0, behavior: "smooth" });
    expect(blur).toHaveBeenCalled();
  });
});
