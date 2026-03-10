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

import { ComponentFixture, TestBed } from "@angular/core/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ContainerTemplatesComponent } from "./container-templates.component";
import { ContainerTemplateService } from "../../../services/container-template/container-template.service";
import { AuthService } from "../../../services/auth/auth.service";
import { DialogService } from "src/app/services/dialog/dialog.service";
import { signal } from "@angular/core";
import { ContainerTemplate } from "../../../services/container/container.service";
import { By } from "@angular/platform-browser";

describe("ContainerTemplatesComponent", () => {
  let component: ContainerTemplatesComponent;
  let fixture: ComponentFixture<ContainerTemplatesComponent>;

  const mockTemplates: ContainerTemplate[] = [
    { name: "Template-A", container_type: "Type-1", default: true, template_options: { tokens: [] } },
    { name: "Template-B", container_type: "Type-2", default: false, template_options: { tokens: [] } }
  ];

  const mockContainerTemplateService = {
    templates: signal(mockTemplates)
  };

  const mockAuthService = {
    isAdmin: signal(true)
  };

  const mockDialogService = {
    openDialog: jest.fn()
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTemplatesComponent, NoopAnimationsModule],
      providers: [
        { provide: ContainerTemplateService, useValue: mockContainerTemplateService },
        { provide: AuthService, useValue: mockAuthService },
        { provide: DialogService, useValue: mockDialogService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTemplatesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should render all templates in the table initially", () => {
    const rows = fixture.debugElement.queryAll(By.css("tr[mat-row]"));
    expect(rows.length).toBe(mockTemplates.length);
  });

  it("should filter items when the filter signal changes", () => {
    const newFilter = component.filter().setValueOfKey("name", "Template-A");
    component.filter.set(newFilter);
    fixture.detectChanges();

    const rows = fixture.debugElement.queryAll(By.css("tr[mat-row]"));
    expect(component.filteredContainerTemplates().length).toBe(1);
    expect(rows.length).toBe(1);
    expect(rows[0].nativeElement.textContent).toContain("Template-A");
  });

  it("should show 'no data' row when filter matches nothing", () => {
    const newFilter = component.filter().setValueOfKey("name", "NonExistent");
    component.filter.set(newFilter);
    fixture.detectChanges();

    const noDataRow = fixture.debugElement.query(By.css(".no-data-cell"));
    expect(noDataRow).toBeTruthy();
    expect(noDataRow.nativeElement.textContent).toContain("No container template matching the filter");
  });

  it("should open edit dialog when a name is clicked", () => {
    const firstLink = fixture.debugElement.query(By.css("td.mat-column-name a"));
    firstLink.nativeElement.click();

    expect(mockDialogService.openDialog).toHaveBeenCalledWith(
      expect.objectContaining({
        data: mockTemplates[0]
      })
    );
  });

  it("should handle selection logic correctly", () => {
    // Select all
    component.toggleAllRows();
    expect(component.selection.selected.length).toBe(mockTemplates.length);

    // Deselect all
    component.toggleAllRows();
    expect(component.selection.isEmpty()).toBeTruthy();
  });

  it("should toggle filter keys when clicking column filter buttons", () => {
    // Click name filter
    component.onClickFilter("name");
    fixture.detectChanges();
    expect(component.filter().hasKey("name")).toBeTruthy();

    // Toggle name filter off
    component.onClickFilter("name");
    fixture.detectChanges();
    expect(component.filter().hasKey("name")).toBeFalsy();
  });

  it("should return the correct filter icon name based on filter state", () => {
    // Default icon
    expect(component.getFilterIconName("name")).toBe("filter_alt");

    expect(typeof component.getFilterIconName("name")).toBe("string");
  });
});
