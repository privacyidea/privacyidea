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
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { PageEvent } from "@angular/material/paginator";
import { Sort } from "@angular/material/sort";
import { ActivatedRoute, NavigationEnd, Router } from "@angular/router";
import { of } from "rxjs";

import { AuthService } from "@services/auth/auth.service";
import { ContainerDetailData, ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { NotificationService } from "@services/notification/notification.service";
import { RealmService } from "@services/realm/realm.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";

import { ContainerTableComponent } from "@components/container/container-table/container-table.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { TokenService } from "@services/token/token.service";
import { expectsTableStateGating } from "@testing/table-state-gating";
import {
  MockContainerService,
  MockContentService,
  MockLocalService,
  MockNotificationService,
  MockTableUtilsService,
  MockTokenService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockRealmService } from "@testing/mock-services/mock-realm-service";
import { ContainerTemplateService } from "@services/container-template/container-template.service";
import { MockContainerTemplateService } from "@testing/mock-services/mock-container-template-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";

describe("ContainerTableComponent (Jest)", () => {
  let component: ContainerTableComponent;
  let fixture: ComponentFixture<ContainerTableComponent>;
  let containerService: MockContainerService;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [ContainerTableComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContainerTemplateService, useClass: MockContainerTemplateService },
        {
          provide: Router,
          useValue: {
            navigate: jest.fn(),
            events: of(new NavigationEnd(0, "/", "/"))
          }
        },
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({ id: "123" })
          }
        },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTableComponent);
    containerService = TestBed.inject(ContainerService) as unknown as MockContainerService;
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("gates the table on its read right, row count and filter", () => {
    expectsTableStateGating({
      state: component.tableState,
      right: "container_list"
    });
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("containerDataSource maps user_name/user_realm from first user entry", () => {
    const withUsers = MockPiResponse.fromValue({
      count: 1,
      containers: [
        {
          serial: "C-1",
          states: [],
          realms: [],
          tokens: [],
          type: "generic",
          description: "d",
          users: [{ user_name: "alice", user_realm: "r1", user_resolver: "", user_id: "" }]
        }
      ]
    });

    containerService.containerResource.set(withUsers);
    fixture.detectChanges();

    const row = component.containerDataSource().data[0];
    expect(row.user_name).toBe("alice");
    expect(row.user_realm).toBe("r1");
  });

  describe("template column and comparison column", () => {
    const containerWithSerial = (serial: string, template?: string) => ({
      serial,
      template,
      states: [],
      realms: [],
      tokens: [],
      type: "generic",
      description: "",
      users: []
    });

    const cellTexts = (columnClass: string) =>
      Array.from(fixture.nativeElement.querySelectorAll(`td.mat-column-${columnClass}`)).map((cell) =>
        (cell as HTMLElement).textContent?.replace(/\s+/g, " ").trim()
      );

    beforeEach(() => {
      containerService.containerResource.set(
        MockPiResponse.fromValue({
          count: 4,
          containers: [
            containerWithSerial("C-1", "base"),
            containerWithSerial("C-2", "base"),
            containerWithSerial("C-3"),
            containerWithSerial("C-4")
          ]
        })
      );
      fixture.detectChanges();
    });

    it("always shows the template column with the template names and a header filter button", () => {
      const header = fixture.nativeElement.querySelector("th.mat-column-template");
      expect(header.textContent).toContain("Template");
      expect(header.querySelector("button.filter-button")).not.toBeNull();
      expect(header.querySelector("button.sort-button")).toBeNull();
      expect(cellTexts("template")).toEqual(["base", "base", "", ""]);
    });

    it("offers the template filter options in the header filter menu", async () => {
      fixture.nativeElement.querySelector("th.mat-column-template button.filter-button").click();
      fixture.detectChanges();
      await fixture.whenStable();

      const menuText = document.querySelector(".mat-mdc-menu-panel")?.textContent ?? "";
      expect(menuText).toContain("Clear Filter");
      expect(document.querySelector(".mat-mdc-menu-panel mat-icon")?.textContent).toContain("filter_alt_off");
      expect(menuText).toContain("With template");
      expect(menuText).toContain("Without template");
    });

    it("has no template entry in the toolbar advanced filter menu", () => {
      expect(component.toolbarFilterKeys).not.toContain("template");
      expect(component.toolbarFilterKeys).toContain("assigned");
    });

    it("shows no differences column before a comparison", () => {
      expect(fixture.nativeElement.querySelector("th.mat-column-differences")).toBeNull();
    });

    it("renders template names and differences with their status classes", () => {
      component.showComparison([
        { containerSerial: "C-1", templateName: "base", equal: false, missing: ["hotp"], additional: ["totp"] },
        { containerSerial: "C-2", templateName: "base", equal: true, missing: [], additional: [] },
        { containerSerial: "C-3", templateName: "", equal: null, missing: [], additional: [] }
      ]);
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector("th.mat-column-differences").textContent).toContain("Differences");
      expect(cellTexts("differences")).toEqual(["- hotp + totp", "Equal", "", ""]);
      const missing = fixture.nativeElement.querySelector("td.mat-column-differences .highlight-false");
      const additional = fixture.nativeElement.querySelector("td.mat-column-differences .highlight-warning");
      expect(missing.textContent.trim()).toBe("- hotp");
      expect(additional.textContent.trim()).toBe("+ totp");
    });

    it("keeps earlier results when further containers are compared", () => {
      component.showComparison([
        { containerSerial: "C-1", templateName: "base", equal: true, missing: [], additional: [] }
      ]);
      component.showComparison([
        { containerSerial: "C-2", templateName: "other", equal: true, missing: [], additional: [] }
      ]);
      fixture.detectChanges();

      expect(cellTexts("differences")).toEqual(["Equal", "Equal", "", ""]);
    });

    it("removes the differences column and the results when the comparison is hidden", () => {
      component.showComparison([
        { containerSerial: "C-1", templateName: "base", equal: true, missing: [], additional: [] }
      ]);
      fixture.detectChanges();

      component.hideComparison();
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector("th.mat-column-differences")).toBeNull();
      expect(fixture.nativeElement.querySelector("th.mat-column-template")).not.toBeNull();
      expect(component.comparisonByContainerSerial()).toEqual({});
    });
  });

  describe("#handleStateClick", () => {
    it("calls toggleActive and reloads data", () => {
      const element: ContainerDetailData = {
        serial: "CONT-1",
        states: ["active"],
        realms: [],
        tokens: [],
        type: "",
        users: []
      };
      component.handleStateClick(element);

      expect(containerService.toggleActive).toHaveBeenCalledWith("CONT-1", ["active"]);
      expect(containerService.containerResource.reload).toHaveBeenCalled();
    });
  });

  describe("#onPageEvent", () => {
    it("updates page index, size and eventPageSize", () => {
      const event: PageEvent = {
        pageIndex: 2,
        pageSize: 15,
        length: 100,
        previousPageIndex: 1
      };

      component.onPageEvent(event);
      fixture.detectChanges();

      expect(component.pageIndex()).toBe(2);
      expect(component.pageSize()).toBe(15);
      expect(containerService.eventPageSize()).toBe(15);
    });
  });

  describe("#onSortEvent", () => {
    it("updates the sort signal", () => {
      const sort: Sort = { active: "type", direction: "asc" };
      component.onSortEvent(sort);

      const result = component.sort();
      expect(result.active).toBe("type");
      expect(result.direction).toBe("asc");
    });
  });

  describe("#onFilterInput", () => {
    it("applies the filter while typing as long as no user or realm filter is used", () => {
      const inputEvent = { target: { value: "type: generic" } } as unknown as Event;

      component.onFilterInput(inputEvent);

      expect(containerService.handleFilterInput).toHaveBeenCalledWith(inputEvent);
    });

    it("defers the user and the realm filter until the input is confirmed", () => {
      component.onFilterInput({ target: { value: "user: alice" } } as unknown as Event);
      expect(containerService.handleFilterInput).not.toHaveBeenCalled();

      component.onFilterInput({ target: { value: "realm: realm1" } } as unknown as Event);
      expect(containerService.handleFilterInput).not.toHaveBeenCalled();
    });

    it("hints that the filter has to be confirmed while a user filter is typed", () => {
      component.onFilterInput({ target: { value: "user: alice" } } as unknown as Event);

      expect(component.showFilterHint()).toBe(true);
    });

    it("does not hint once the typed filter is the applied one", () => {
      containerService.activeFilter.set(new FilterValue({ value: "user: alice" }));
      component.onFilterInput({ target: { value: "user: alice" } } as unknown as Event);

      expect(component.showFilterHint()).toBe(false);
    });

    it("does not hint for a filter that is applied while typing", () => {
      component.onFilterInput({ target: { value: "type: generic" } } as unknown as Event);

      expect(component.showFilterHint()).toBe(false);
    });
  });

  describe("Selection", () => {
    it("exposes the selection held by the container service", () => {
      const containerDetailData: ContainerDetailData = {
        serial: "CONT-1",
        states: [],
        realms: [],
        tokens: [],
        type: "",
        users: []
      };
      containerService.setContainerSelection([containerDetailData, { ...containerDetailData, serial: "CONT-2" }]);

      expect(component.containerSelection).toBe(containerService.containerSelection);
      expect(component.containerSelection.selectedRows().map((row) => row.serial)).toEqual(["CONT-1", "CONT-2"]);
      expect(component.containerSelection.allRowsSelected()).toBe(true);
    });
  });

  describe("assigned filter", () => {
    let tableUtilsService: MockTableUtilsService;

    beforeEach(() => {
      tableUtilsService = TestBed.inject(TableUtilsService) as unknown as MockTableUtilsService;
      containerService.updateFilter.mockImplementation((update: (current: FilterValue) => FilterValue) =>
        containerService.activeFilter.set(update(containerService.activeFilter()))
      );
      tableUtilsService.toggleBooleanInFilter.mockImplementation(
        ({ keyword, currentValue }: { keyword: string; currentValue: FilterValue }) =>
          currentValue.toggleBooleanKey(keyword)
      );
    });

    it("cycles through true, false and cleared like the actions menu does", () => {
      component.toggleFilter("assigned");
      expect(containerService.activeFilter().getValueOfKey("assigned")).toBe("true");

      component.toggleFilter("assigned");
      expect(containerService.activeFilter().getValueOfKey("assigned")).toBe("false");

      component.toggleFilter("assigned");
      expect(containerService.activeFilter().hasKey("assigned")).toBe(false);
    });

    it("leaves other keywords to the keyword toggle", () => {
      tableUtilsService.toggleKeywordInFilter.mockReturnValue(new FilterValue({ value: "type: generic" }));

      component.toggleFilter("type");

      expect(tableUtilsService.toggleKeywordInFilter).toHaveBeenCalledWith({
        keyword: "type",
        currentValue: expect.any(FilterValue)
      });
      expect(tableUtilsService.toggleBooleanInFilter).not.toHaveBeenCalled();
    });

    it("shows the icon for the unset, true and false state", () => {
      expect(component.getFilterIconName("assigned")).toBe("filter_alt");

      containerService.activeFilter.set(new FilterValue({ value: "assigned: true" }));
      expect(component.getFilterIconName("assigned")).toBe("screen_rotation_alt");

      containerService.activeFilter.set(new FilterValue({ value: "assigned: false" }));
      expect(component.getFilterIconName("assigned")).toBe("filter_alt_off");
    });
  });

  describe("Accessibility labels", () => {
    it("selectRowLabel names the container serial", () => {
      expect((component as unknown as { selectRowLabel: (serial: string) => string }).selectRowLabel("CONT-1")).toBe(
        "Select container CONT-1"
      );
    });
  });

  describe("inline cell filter", () => {
    it("filters by the user together with the row's realm", () => {
      component.filterByUser("alice", "realm1");

      expect(containerService.activeFilter().getValueOfKey("user")).toBe("alice");
      expect(containerService.activeFilter().getValueOfKey("realm")).toBe("realm1");
    });

    it("filters by the user alone when the row has no realm", () => {
      component.filterByUser("alice", "");

      expect(containerService.activeFilter().getValueOfKey("user")).toBe("alice");
      expect(containerService.activeFilter().hasKey("realm")).toBe(false);
    });
  });

  describe("template filter", () => {
    it("filters for containers with any template", () => {
      component.onTemplateFilterSelected("with-template");

      expect(containerService.activeFilter().getValueOfKey("template")).toBe("any");
      expect(containerService.activeFilter().hasKey("has_template")).toBe(false);
    });

    it("filters for containers without a template", () => {
      component.onTemplateFilterSelected("without-template");

      expect(containerService.activeFilter().getValueOfKey("template")).toBe("none");
    });

    it("filters by a selected template and clears previous template conditions", () => {
      containerService.activeFilter.set(new FilterValue({ value: "template: none" }));

      component.onTemplateFilterSelected("specific", "baseline");

      expect(containerService.activeFilter().getValueOfKey("template")).toBe("=baseline");
      expect(containerService.activeFilter().hasKey("has_template")).toBe(false);
    });

    it("clears only template conditions when Clear Filter is selected", () => {
      containerService.activeFilter.set(new FilterValue({ value: "template: baseline type: smartphone" }));

      component.onTemplateFilterSelected("all");

      expect(containerService.activeFilter().hasKey("type")).toBe(true);
      expect(containerService.activeFilter().hasKey("template")).toBe(false);
      expect(containerService.activeFilter().hasKey("has_template")).toBe(false);
    });
  });
});
