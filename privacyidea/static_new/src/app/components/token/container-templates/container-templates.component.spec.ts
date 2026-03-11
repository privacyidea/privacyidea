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
import { MatCheckboxChange } from "@angular/material/checkbox";

describe("ContainerTemplatesComponent", () => {
  let component: ContainerTemplatesComponent;
  let fixture: ComponentFixture<ContainerTemplatesComponent>;

  const mockTemplates: ContainerTemplate[] = [
    { name: "Template-C", container_type: "Type-1", default: false, template_options: { tokens: [] } },
    { name: "Template-A", container_type: "Type-1", default: true, template_options: { tokens: [] } },
    { name: "Template-B", container_type: "Type-2", default: false, template_options: { tokens: [] } }
  ];

  const templatesSignal = signal<ContainerTemplate[]>(mockTemplates);

  const mockContainerTemplateService = {
    templates: templatesSignal
  };

  const mockAuthService = {
    isAdmin: signal(true)
  };

  const mockDialogService = {
    openDialog: jest.fn()
  };

  beforeEach(async () => {
    templatesSignal.set(mockTemplates);
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

  it("should show skeleton rows when service returns no templates", () => {
    templatesSignal.set([]);
    fixture.detectChanges();

    const rows = fixture.debugElement.queryAll(By.css("tr[mat-row]"));

    expect(rows.length).toBe(component.pageSize());
    expect(rows[0].classes["skeleton-row"]).toBeTruthy();
  });

  it("should disable header checkbox when in skeleton state", () => {
    templatesSignal.set([]);
    fixture.detectChanges();

    const headerCheckbox = fixture.debugElement.query(By.css("th.mat-column-select mat-checkbox"));
    expect(headerCheckbox.componentInstance.disabled).toBeTruthy();
  });

  it("should respect pageSize and slice data accordingly", () => {
    component.pageSize.set(2);
    fixture.detectChanges();

    const displayedRows = fixture.debugElement.queryAll(By.css("tr[mat-row]"));
    expect(displayedRows.length).toBe(2);
    expect(component.pagedContainerTemplates().length).toBe(2);
  });

  it("should change page and update displayed data", () => {
    component.pageSize.set(1);
    component.pageIndex.set(1);
    fixture.detectChanges();

    const rows = fixture.debugElement.queryAll(By.css("tr[mat-row]"));
    expect(rows[0].nativeElement.textContent).toContain("Template-A");
  });

  it("should reset pageIndex to 0 when filter changes", () => {
    component.pageIndex.set(1);
    component.onFilterChange(component.filter().setValueOfKey("name", "A"));
    expect(component.pageIndex()).toBe(0);
  });

  it("should only select displayed rows on the current page when toggleAllRows is called", () => {
    component.pageSize.set(1);
    fixture.detectChanges();

    component.toggleAllRows();
    expect(component.selectedTemplateNames().size).toBe(1);
    expect(component.selectedTemplateNames().has("Template-C")).toBeTruthy();
    expect(component.selectedTemplates().length).toBe(1);
  });

  it("should clear selection when page changes", () => {
    component.pageSize.set(1);
    fixture.detectChanges();
    component.toggleAllRows();

    component.pageIndex.set(1);
    fixture.detectChanges();

    expect(component.selectedTemplateNames().size).toBe(0);
  });

  it("should update selection when updateSelection is called", () => {
    const template = mockTemplates[0];
    component.updateSelection({ checked: true } as MatCheckboxChange, template);
    expect(component.selectedTemplateNames().has(template.name)).toBeTruthy();
    expect(component.selectedTemplates()[0].name).toBe(template.name);

    component.updateSelection({ checked: false } as MatCheckboxChange, template);
    expect(component.selectedTemplateNames().has(template.name)).toBeFalsy();
  });

  it("should reduce selection when pageSize changes from 10 to 1 and update child component", () => {
    component.pageSize.set(10);
    fixture.detectChanges();

    component.toggleAllRows();
    fixture.detectChanges();
    expect(component.selectedTemplates().length).toBe(3);

    component.pageSize.set(1);
    fixture.detectChanges();

    expect(component.selectedTemplates().length).toBe(1);

    const actionComponent = fixture.debugElement.query(
      By.css("app-container-templates-table-actions")
    ).componentInstance;

    expect(actionComponent.selectedTemplates().length).toBe(1);
    expect(actionComponent.selectedTemplates()[0].name).toBe("Template-C");
  });
  it("should open edit dialog only if row is not a skeleton row", () => {
    component.openEditDialog(mockTemplates[0]);
    expect(mockDialogService.openDialog).toHaveBeenCalled();

    mockDialogService.openDialog.mockClear();
    component.openEditDialog({ name: "" } as ContainerTemplate);
    expect(mockDialogService.openDialog).not.toHaveBeenCalled();
  });

  it("should filter items and update totalLength", () => {
    const newFilter = component.filter().setValueOfKey("name", "Template-A");
    component.filter.set(newFilter);
    fixture.detectChanges();

    expect(component.totalLength()).toBe(1);
    const rows = fixture.debugElement.queryAll(By.css("tr[mat-row]"));
    expect(rows.length).toBe(1);
  });

  it("should show 'no data' row when filter matches nothing and templates exist", () => {
    const newFilter = component.filter().setValueOfKey("name", "NonExistent");
    component.filter.set(newFilter);
    fixture.detectChanges();

    const noDataRow = fixture.debugElement.query(By.css("tr.mat-mdc-no-data-row"));
    expect(noDataRow).toBeTruthy();
    expect(noDataRow.nativeElement.textContent).toContain("No data matching the filter.");
  });

  it("should toggle filter keys and reset pageIndex when clicking header filter buttons", () => {
    component.pageIndex.set(1);
    const filterButton = fixture.debugElement.query(By.css(".col-name .filter-button"));

    filterButton.nativeElement.click();
    fixture.detectChanges();

    expect(component.filter().hasKey("name")).toBeTruthy();
    expect(component.pageIndex()).toBe(0);

    filterButton.nativeElement.click();
    fixture.detectChanges();

    expect(component.filter().hasKey("name")).toBeFalsy();
  });

  it("should return correct icon names for different filter action types", () => {
    expect(component.getFilterIconName("name")).toBe("filter_alt");

    const activeFilter = component.filter().toggleKey("name");
    component.filter.set(activeFilter);

    expect(component.getFilterIconName("name")).toBe("filter_alt_off");
  });

  it("should sort data by name ascending", () => {
    component.onSortChange({ active: "name", direction: "asc" });
    fixture.detectChanges();

    const data = component.pagedContainerTemplates();
    expect(data[0].name).toBe("Template-A");
  });

  it("should sort data by name descending", () => {
    component.onSortChange({ active: "name", direction: "desc" });
    fixture.detectChanges();

    const data = component.pagedContainerTemplates();
    expect(data[0].name).toBe("Template-C");
  });

  it("should sort data by boolean 'default' column", () => {
    component.onSortChange({ active: "default", direction: "desc" });
    fixture.detectChanges();

    const data = component.pagedContainerTemplates();
    expect(data[0].default).toBe(true);
    expect(data[1].default).toBe(false);
  });

  it("should return unsorted data if sort direction is empty", () => {
    component.onSortChange({ active: "name", direction: "" });
    fixture.detectChanges();

    const data = component.pagedContainerTemplates();
    expect(data).toEqual(mockTemplates);
  });

  it("should have the correct colspan in the 'no data' row based on columnKeys", () => {
    const newFilter = component.filter().setValueOfKey("name", "NonExistent");
    component.filter.set(newFilter);
    fixture.detectChanges();

    const noDataCell = fixture.debugElement.query(By.css("tr.mat-mdc-no-data-row td"));
    const expectedColspan = component.columnKeys().length;

    expect(noDataCell.attributes["colspan"]).toBe(expectedColspan.toString());
  });
});
