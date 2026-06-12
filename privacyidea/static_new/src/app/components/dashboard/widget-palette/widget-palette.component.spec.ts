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
import { OverlayContainer } from "@angular/cdk/overlay";
import { provideZonelessChangeDetection } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { DashboardLayoutService } from "@services/dashboard/dashboard-layout.service";
import { WidgetRegistryService } from "@services/dashboard/widget-registry.service";
import { WidgetPaletteComponent } from "./widget-palette.component";

describe("WidgetPaletteComponent", () => {
  let fixture: ComponentFixture<WidgetPaletteComponent>;
  let component: WidgetPaletteComponent;
  let layoutService: DashboardLayoutService;
  let registry: WidgetRegistryService;
  let overlayContainer: OverlayContainer;
  let overlayContainerElement: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WidgetPaletteComponent],
      providers: [provideZonelessChangeDetection()]
    }).compileComponents();

    layoutService = TestBed.inject(DashboardLayoutService);
    registry = TestBed.inject(WidgetRegistryService);
    overlayContainer = TestBed.inject(OverlayContainer);
    overlayContainerElement = overlayContainer.getContainerElement();
    layoutService.widgets.set([]);

    fixture = TestBed.createComponent(WidgetPaletteComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    fixture.destroy();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should render a single add-widget trigger button", () => {
    const buttons = fixture.nativeElement.querySelectorAll("button");
    expect(buttons.length).toBe(1);
  });

  it("should open a menu with one item per non-pinned widget type", () => {
    fixture.nativeElement.querySelector("button").click();
    fixture.detectChanges();

    const items = overlayContainerElement.querySelectorAll(".mat-mdc-menu-item");
    expect(items.length).toBe(registry.widgetTypes.filter((widget) => !widget.pinned).length);
  });

  it("should add the corresponding widget when a menu item is clicked", () => {
    const addSpy = jest.spyOn(layoutService, "addWidget");
    const firstType = registry.widgetTypes.filter((widget) => !widget.pinned)[0].type;

    fixture.nativeElement.querySelector("button").click();
    fixture.detectChanges();
    (overlayContainerElement.querySelector(".mat-mdc-menu-item") as HTMLButtonElement).click();

    expect(addSpy).toHaveBeenCalledWith(firstType);
  });

  it("should delegate add() to the layout service", () => {
    const addSpy = jest.spyOn(layoutService, "addWidget");
    component['add']("events");
    expect(addSpy).toHaveBeenCalledWith("events");
  });

  it("should not render a menu item for a widget type that is already placed", () => {
    const nonPinned = registry.widgetTypes.filter((widget) => !widget.pinned);
    layoutService.addWidget(nonPinned[0].type);
    fixture.detectChanges();

    fixture.nativeElement.querySelector("button").click();
    fixture.detectChanges();

    const items = overlayContainerElement.querySelectorAll(".mat-mdc-menu-item");
    expect(items.length).toBe(nonPinned.length - 1);
  });

  it("should hide the add-widget button when every widget type is already placed", () => {
    registry.widgetTypes.filter((widget) => !widget.pinned).forEach((widget) => layoutService.addWidget(widget.type));
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("button")).toBeNull();
  });
});
