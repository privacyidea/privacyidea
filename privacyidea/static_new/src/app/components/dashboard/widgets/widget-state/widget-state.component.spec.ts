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
import { provideZonelessChangeDetection } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { WidgetState } from "@models/dashboard";
import { WidgetStateComponent } from "./widget-state.component";

describe("WidgetStateComponent", () => {
  let fixture: ComponentFixture<WidgetStateComponent>;
  let component: WidgetStateComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WidgetStateComponent],
      providers: [provideZonelessChangeDetection()]
    }).compileComponents();

    fixture = TestBed.createComponent(WidgetStateComponent);
    component = fixture.componentInstance;
  });

  function render(state: WidgetState): void {
    fixture.componentRef.setInput("state", state);
    fixture.detectChanges();
  }

  it("should create", () => {
    render("loading");
    expect(component).toBeTruthy();
  });

  it("should show a spinner while loading", () => {
    render("loading");
    expect(fixture.nativeElement.querySelector("mat-progress-spinner")).toBeTruthy();
    expect(fixture.nativeElement.textContent).not.toContain("Loading");
  });

  it("should show a denied message", () => {
    render("denied");
    expect(fixture.nativeElement.querySelector("mat-progress-spinner")).toBeNull();
    expect(fixture.nativeElement.textContent).toContain("not allowed");
  });

  it("should show an error message", () => {
    render("error");
    expect(fixture.nativeElement.textContent).toContain("Could not load data");
  });

  it("should project content only when ready", () => {
    render("ready");
    expect(fixture.nativeElement.querySelector("mat-progress-spinner")).toBeNull();
    expect(fixture.nativeElement.querySelector(".widget-state-status")).toBeNull();
  });
});
