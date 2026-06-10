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
import { DashboardWidget } from "@models/dashboard";
import { WelcomeWidgetComponent } from "./welcome-widget.component";

describe("WelcomeWidgetComponent", () => {
  let fixture: ComponentFixture<WelcomeWidgetComponent>;
  let component: WelcomeWidgetComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WelcomeWidgetComponent],
      providers: [provideZonelessChangeDetection()]
    }).compileComponents();

    fixture = TestBed.createComponent(WelcomeWidgetComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should extend the DashboardWidget base", () => {
    expect(component).toBeInstanceOf(DashboardWidget);
  });

  it("should render a welcome message", () => {
    expect(fixture.nativeElement.textContent).toContain("Welcome");
  });

  it("should override the static metadata", () => {
    expect(WelcomeWidgetComponent.type).toBe("welcome");
    expect(WelcomeWidgetComponent.title).toBeTruthy();
    expect(WelcomeWidgetComponent.icon).toBe("waving_hand");
  });

  it("should override the static size constraints", () => {
    expect(WelcomeWidgetComponent.defaultSize).toEqual({ cols: 8, rows: 4 });
    expect(WelcomeWidgetComponent.minSize).toEqual({ cols: 5, rows: 3 });
    expect(WelcomeWidgetComponent.maxSize).toEqual({ cols: 12, rows: 6 });
  });
});
