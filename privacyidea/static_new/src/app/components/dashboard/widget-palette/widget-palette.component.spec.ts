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
import { DashboardLayoutService } from "@services/dashboard/dashboard-layout.service";
import { WidgetRegistryService } from "@services/dashboard/widget-registry.service";
import { WidgetPaletteComponent } from "./widget-palette.component";

describe("WidgetPaletteComponent", () => {
  let fixture: ComponentFixture<WidgetPaletteComponent>;
  let component: WidgetPaletteComponent;
  let layoutService: DashboardLayoutService;
  let registry: WidgetRegistryService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WidgetPaletteComponent],
      providers: [provideZonelessChangeDetection()]
    }).compileComponents();

    layoutService = TestBed.inject(DashboardLayoutService);
    registry = TestBed.inject(WidgetRegistryService);

    fixture = TestBed.createComponent(WidgetPaletteComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should render one button per registered widget type", () => {
    const buttons = fixture.nativeElement.querySelectorAll("button");
    expect(buttons.length).toBe(registry.widgetTypes.length);
  });

  it("should add the corresponding widget when a palette button is clicked", () => {
    const addSpy = jest.spyOn(layoutService, "addWidget");
    const firstType = registry.widgetTypes[0].type;

    fixture.nativeElement.querySelector("button").click();

    expect(addSpy).toHaveBeenCalledWith(firstType);
  });

  it("should delegate add() to the layout service", () => {
    const addSpy = jest.spyOn(layoutService, "addWidget");
    component['add']("stat");
    expect(addSpy).toHaveBeenCalledWith("stat");
  });
});
