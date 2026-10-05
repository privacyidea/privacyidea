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

import { Component, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatIcon } from "@angular/material/icon";
import { MatTooltip } from "@angular/material/tooltip";
import { By } from "@angular/platform-browser";
import { TooltipAriaLabelDirective } from "./tooltip-aria-label.directive";

@Component({
  standalone: true,
  imports: [MatIcon, MatTooltip, TooltipAriaLabelDirective],
  template: `
    <button id="icon" [matTooltip]="tip()"><mat-icon aria-hidden="true">refresh</mat-icon></button>
    <button id="text" matTooltip="Tip">Visible text</button>
    <button id="labelled" aria-label="Own name" matTooltip="Tip"><mat-icon aria-hidden="true">x</mat-icon></button>
    <button id="labelledby" aria-labelledby="other" matTooltip="Tip"><mat-icon aria-hidden="true">x</mat-icon></button>
    <a id="link" href="/x" matTooltip="Go"><mat-icon aria-hidden="true">x</mat-icon></a>
    <span id="span" matTooltip="Not a control"></span>
    <button id="empty" matTooltip=""><mat-icon aria-hidden="true">x</mat-icon></button>
  `
})
class HostComponent {
  tip = signal("Refresh Resources");
}

describe("TooltipAriaLabelDirective", () => {
  let fixture: ComponentFixture<HostComponent>;
  const el = (id: string): HTMLElement => fixture.debugElement.query(By.css("#" + id)).nativeElement;

  beforeEach(() => {
    fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
  });

  it("names an icon-only button with its tooltip", () => {
    expect(el("icon").getAttribute("aria-label")).toBe("Refresh Resources");
  });

  it("follows the tooltip when it changes", () => {
    fixture.componentInstance.tip.set("Reload");
    fixture.detectChanges();

    expect(el("icon").getAttribute("aria-label")).toBe("Reload");
  });

  it("names an icon-only link", () => {
    expect(el("link").getAttribute("aria-label")).toBe("Go");
  });

  it("leaves a button with visible text alone", () => {
    expect(el("text").hasAttribute("aria-label")).toBe(false);
  });

  it("keeps an aria-label the element sets itself", () => {
    expect(el("labelled").getAttribute("aria-label")).toBe("Own name");
  });

  it("keeps an aria-labelledby the element sets itself", () => {
    expect(el("labelledby").hasAttribute("aria-label")).toBe(false);
  });

  it("does not touch elements that are not buttons or links", () => {
    expect(el("span").hasAttribute("aria-label")).toBe(false);
  });

  it("sets no label for an empty tooltip", () => {
    expect(el("empty").hasAttribute("aria-label")).toBe(false);
  });
});
