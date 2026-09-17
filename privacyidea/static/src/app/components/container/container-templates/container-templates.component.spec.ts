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

import { signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { provideRouter, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService } from "@services/auth/auth.service";
import { ContainerTemplateService } from "@services/container-template/container-template.service";
import { ContainerTemplate } from "@services/container/container.service";
import { DialogService } from "@services/dialog/dialog.service";
import { ContainerTemplatesComponent } from "./container-templates.component";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { expectsTableStateGating } from "@testing/table-state-gating";

describe("ContainerTemplatesComponent", () => {
  let component: ContainerTemplatesComponent;
  let fixture: ComponentFixture<ContainerTemplatesComponent>;

  const mockTemplates: ContainerTemplate[] = [
    { name: "Template-C", container_type: "Type-1", default: false, template_options: { tokens: [] } },
    { name: "Template-A", container_type: "Type-1", default: true, template_options: { tokens: [] } },
    { name: "Template-B", container_type: "Type-2", default: false, template_options: { tokens: [] } }
  ];

  const templatesSignal = signal<ContainerTemplate[]>(mockTemplates);
  const templatesLoaded = signal(true);

  const mockContainerTemplateService = {
    templates: templatesSignal,
    availableContainerTypes: signal<string[]>(["generic", "smartphone"]),
    templatesResource: {
      hasValue: () => templatesLoaded(),
      error: () => null,
      isLoading: () => false,
      reload: jest.fn()
    }
  };

  const mockDialogService = {
    openDialog: jest.fn()
  };

  beforeEach(async () => {
    templatesSignal.set(mockTemplates);
    templatesLoaded.set(true);
    await TestBed.configureTestingModule({
      imports: [ContainerTemplatesComponent],
      providers: [
        { provide: ContainerTemplateService, useValue: mockContainerTemplateService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: DialogService, useValue: mockDialogService },
        provideRouter([])
      ]
    }).compileComponents();

    (TestBed.inject(AuthService) as unknown as MockAuthService).authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,

      rights: ["container_template_list"]
    });

    fixture = TestBed.createComponent(ContainerTemplatesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("gates the table on its read right, row count and filter", () => {
    expectsTableStateGating({
      state: component.tableState,
      right: "container_template_list"
    });
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("stands the state panel in for the table while the templates are still loading for the first time", () => {
    // A fresh fixture: the resource has never resolved yet, unlike the shared one above (which
    // beforeEach already resolves once) - this is what a genuine first load looks like.
    templatesSignal.set([]);
    templatesLoaded.set(false);
    const freshFixture = TestBed.createComponent(ContainerTemplatesComponent);
    freshFixture.detectChanges();

    expect(freshFixture.componentInstance.tableState.status()).toBe("loading");
    expect(freshFixture.componentInstance.tableState.showTable()).toBe(false);
    expect(freshFixture.debugElement.queryAll(By.css("tr[mat-row]")).length).toBe(0);
    expect(freshFixture.debugElement.query(By.css("mat-progress-spinner"))).toBeTruthy();
  });

  it("keeps showing the already-loaded rows while a reload is in flight, instead of blanking to the loading panel", () => {
    // Angular's httpResource clears hasValue() the instant a reload starts (a filter/page/sort
    // change), well before the new response arrives - this must not be mistaken for "never loaded"
    // and tear the table (and the currently-focused filter input) down from under the user.
    templatesLoaded.set(false);
    fixture.detectChanges();

    expect(component.tableState.status()).toBe("ready");
    expect(component.tableState.showTable()).toBe(true);
    expect(fixture.debugElement.queryAll(By.css("tr[mat-row]")).length).toBe(mockTemplates.length);
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

  it("should only select displayed rows on the current page", () => {
    component.pageSize.set(1);
    fixture.detectChanges();

    component.selector.selectAllRows();

    expect(component.selector.selectedRows().map((template) => template.name)).toEqual(["Template-C"]);
    expect(component.selector.allRowsSelected()).toBe(true);
  });

  it("should clear selection when page changes", () => {
    component.pageSize.set(1);
    fixture.detectChanges();
    component.selector.selectAllRows();

    component.pageIndex.set(1);
    fixture.detectChanges();

    expect(component.selector.hasSelection()).toBe(false);
  });

  it("should reduce selection when pageSize changes from 10 to 1 and update child component", () => {
    component.pageSize.set(10);
    fixture.detectChanges();

    component.selector.selectAllRows();
    fixture.detectChanges();
    expect(component.selector.selectedCount()).toBe(3);

    component.pageSize.set(1);
    fixture.detectChanges();

    expect(component.selector.selectedCount()).toBe(1);

    const actionComponent = fixture.debugElement.query(
      By.css("app-container-templates-table-actions")
    ).componentInstance;

    expect(actionComponent.selectedTemplates().length).toBe(1);
    expect(actionComponent.selectedTemplates()[0].name).toBe("Template-C");
  });
  it("should navigate to details route only if row is not a skeleton row", () => {
    const router = TestBed.inject(Router);
    const navigateSpy = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);

    component.onClickTemplateName(mockTemplates[0]);
    expect(navigateSpy).toHaveBeenCalledWith(ROUTE_PATHS.CONTAINERS_TEMPLATES_DETAILS + mockTemplates[0].name);

    navigateSpy.mockClear();
    component.onClickTemplateName({ name: "" } as ContainerTemplate);
    expect(navigateSpy).not.toHaveBeenCalled();
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
    expect(noDataRow.nativeElement.textContent).toContain("No entries match the filter");
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

  it("cycles the default filter through true, false and off", () => {
    component.onClickFilter("default");
    expect(component.filter().getFilterOfKey("default")).toBe("true");
    expect(component.getFilterIconName("default")).toBe("screen_rotation_alt");
    expect(component.pagedContainerTemplates().map((t) => t.name)).toEqual(["Template-A"]);

    component.onClickFilter("default");
    expect(component.filter().getFilterOfKey("default")).toBe("false");
    expect(component.getFilterIconName("default")).toBe("filter_alt_off");
    expect(component.pagedContainerTemplates().map((t) => t.name)).toEqual(["Template-C", "Template-B"]);

    component.onClickFilter("default");
    expect(component.filter().hasKey("default")).toBe(false);
    expect(component.getFilterIconName("default")).toBe("filter_alt");
  });

  it("filters by the selected container type and clears it again", () => {
    component.onContainerTypeSelected("Type-2");
    expect(component.filter().getFilterOfKey("container_type")).toBe("Type-2");
    expect(component.pagedContainerTemplates().map((t) => t.name)).toEqual(["Template-B"]);

    component.onContainerTypeSelected(undefined);
    expect(component.filter().hasKey("container_type")).toBe(false);
  });
});
