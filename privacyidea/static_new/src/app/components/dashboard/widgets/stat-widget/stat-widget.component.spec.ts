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
import { DashboardWidget, WidgetInstance } from "@models/dashboard";
import { StatWidgetComponent } from "./stat-widget.component";

describe("StatWidgetComponent", () => {
  let fixture: ComponentFixture<StatWidgetComponent>;
  let component: StatWidgetComponent;

  const instance: WidgetInstance = { id: "stat-1", type: "stat", x: 0, y: 0, cols: 4, rows: 4 };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StatWidgetComponent],
      providers: [provideZonelessChangeDetection()]
    }).compileComponents();

    fixture = TestBed.createComponent(StatWidgetComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("instance", instance);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should extend the DashboardWidget base", () => {
    expect(component).toBeInstanceOf(DashboardWidget);
  });

  it("should render the placeholder statistic content", () => {
    expect(fixture.nativeElement.textContent).toContain("Statistic");
  });

  it("should override the static metadata", () => {
    expect(StatWidgetComponent.type).toBe("stat");
    expect(StatWidgetComponent.title).toBeTruthy();
    expect(StatWidgetComponent.icon).toBe("insights");
  });

  it("should override the static size constraints", () => {
    expect(StatWidgetComponent.defaultSize).toEqual({ cols: 4, rows: 4 });
    expect(StatWidgetComponent.minSize).toEqual({ cols: 3, rows: 3 });
    expect(StatWidgetComponent.maxSize).toEqual({ cols: 12, rows: 8 });
  });
});
