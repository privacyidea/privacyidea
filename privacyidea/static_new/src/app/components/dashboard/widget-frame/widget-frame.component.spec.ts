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
import { WelcomeWidgetComponent } from "@components/dashboard/widgets/welcome-widget/welcome-widget.component";
import { WidgetInstance } from "@models/dashboard";
import { DashboardLayoutService } from "@services/dashboard/dashboard-layout.service";
import { WidgetFrameComponent } from "./widget-frame.component";

describe("WidgetFrameComponent", () => {
  let fixture: ComponentFixture<WidgetFrameComponent>;
  let component: WidgetFrameComponent;
  let layoutService: DashboardLayoutService;

  const welcomeInstance: WidgetInstance = { id: "w1", type: "welcome", x: 0, y: 0, cols: 8, rows: 4 };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WidgetFrameComponent],
      providers: [provideZonelessChangeDetection()]
    }).compileComponents();

    layoutService = TestBed.inject(DashboardLayoutService);
    layoutService.editMode.set(false);

    fixture = TestBed.createComponent(WidgetFrameComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("instance", welcomeInstance);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should resolve the widget type for the instance type", () => {
    expect(component['widgetType']()?.type).toBe("welcome");
  });

  it("should resolve the component to render", () => {
    expect(component['component']()).toBe(WelcomeWidgetComponent);
  });

  it("should pass the instance through to the outlet inputs", () => {
    expect(component['outletInputs']()).toEqual({ instance: welcomeInstance });
  });

  it("should render the widget title", () => {
    expect(fixture.nativeElement.querySelector(".widget-title").textContent).toContain("Welcome");
  });

  it("should hide the remove button in view mode", () => {
    expect(fixture.nativeElement.querySelector(".widget-remove")).toBeNull();
  });

  it("should show the remove button in edit mode", () => {
    layoutService.editMode.set(true);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector(".widget-remove")).not.toBeNull();
  });

  it("should remove the widget from the layout when remove is triggered", () => {
    const removeSpy = jest.spyOn(layoutService, "removeWidget");
    component['remove']();
    expect(removeSpy).toHaveBeenCalledWith("w1");
  });

  it("should remove the widget when the remove button is clicked in edit mode", () => {
    const removeSpy = jest.spyOn(layoutService, "removeWidget");
    layoutService.editMode.set(true);
    fixture.detectChanges();

    fixture.nativeElement.querySelector(".widget-remove").click();

    expect(removeSpy).toHaveBeenCalledWith("w1");
  });
});
