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
import { MatTooltip } from "@angular/material/tooltip";
import { By } from "@angular/platform-browser";
import { Sort } from "@angular/material/sort";
import { provideRouter } from "@angular/router";

import { AuthService } from "@services/auth/auth.service";
import { ContainerDetailData, ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { DocumentationService } from "@services/documentation/documentation.service";
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
  MockDocumentationService,
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
import { grantRights } from "@testing/toolbar-actions";

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
        { provide: DocumentationService, useClass: MockDocumentationService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContainerTemplateService, useClass: MockContainerTemplateService },
        provideRouter([]),
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

  it("links the container serial, its user and its tokens to their details pages", () => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      rights: ["container_list"]
    });
    containerService.containerResource.set(
      MockPiResponse.fromValue({
        count: 1,
        containers: [
          {
            serial: "C-1",
            states: [],
            realms: [],
            tokens: [{ serial: "T-1", tokentype: "hotp" }],
            type: "generic",
            description: "",
            users: [{ user_name: "alice", user_realm: "r1", user_resolver: "", user_id: "" }]
          } as unknown as ContainerDetailData
        ]
      })
    );
    fixture.detectChanges();
    fixture.nativeElement.querySelector("tr[mat-row]").click();
    fixture.detectChanges();

    const hrefOf = (text: string) =>
      Array.from<HTMLAnchorElement>(fixture.nativeElement.querySelectorAll("tbody a"))
        .find((a) => a.textContent?.trim() === text)
        ?.getAttribute("href");
    expect(hrefOf("C-1")).toBe("/containers/details/C-1");
    expect(hrefOf("alice")).toBe("/users/details/alice?realm=r1");
    expect(hrefOf("T-1")).toBe("/tokens/details/T-1");
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

    const comparisonOf = (containerSerial: string, templateName = "base") => ({
      containerSerial,
      templateName,
      equal: true,
      missing: [] as string[],
      additional: [] as string[]
    });

    const fourContainers = () =>
      MockPiResponse.fromValue({
        count: 4,
        containers: [
          containerWithSerial("C-1", "base"),
          containerWithSerial("C-2", "base"),
          containerWithSerial("C-3"),
          containerWithSerial("C-4")
        ]
      });

    const cellTexts = (columnClass: string) =>
      Array.from(fixture.nativeElement.querySelectorAll(`td.mat-column-${columnClass}`)).map((cell) =>
        (cell as HTMLElement).textContent?.replace(/\s+/g, " ").trim()
      );

    beforeEach(() => {
      // The table is only rendered when the read right is granted (TableState "denied" otherwise),
      // and toolbarFilterKeys is read once at construction, so the keys must exist before that.
      const authService = TestBed.inject(AuthService) as unknown as MockAuthService;
      authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["container_list"] });
      containerService.advancedApiFilterKeys = ["token_serial", "template", "assigned"];
      fixture.destroy();
      fixture = TestBed.createComponent(ContainerTableComponent);
      component = fixture.componentInstance;
      containerService.containerResource.set(fourContainers());
      fixture.detectChanges();
    });

    it("shows neither the template nor the differences column and no template toolbar filter before a comparison", () => {
      expect(fixture.nativeElement.querySelector("th.mat-column-template")).toBeNull();
      expect(fixture.nativeElement.querySelector("th.mat-column-differences")).toBeNull();
      expect(component.toolbarFilterKeys).not.toContain("template");
      expect(component.toolbarFilterKeys).toContain("assigned");
    });

    it("shows the template column with the template names and a header filter button while the comparison is visible", () => {
      component.comparisonVisible.set(true);
      fixture.detectChanges();
      const header = fixture.nativeElement.querySelector("th.mat-column-template");
      expect(header.textContent).toContain("Template");
      expect(header.querySelector("button.filter-button")).not.toBeNull();
      expect(header.querySelector("button.sort-button")).toBeNull();
      expect(cellTexts("template")).toEqual(["base", "base", "", ""]);
    });

    it("offers the template filter options in the header filter menu", async () => {
      component.comparisonVisible.set(true);
      fixture.detectChanges();
      fixture.nativeElement.querySelector("th.mat-column-template button.filter-button").click();
      fixture.detectChanges();
      await fixture.whenStable();

      const menuText = document.querySelector(".mat-mdc-menu-panel")?.textContent ?? "";
      expect(menuText).toContain("Clear Filter");
      expect(document.querySelector(".mat-mdc-menu-panel mat-icon")?.textContent).toContain("filter_alt_off");
      expect(menuText).toContain("With template");
      expect(menuText).toContain("Without template");
    });

    it("renders template names and differences with their status classes", () => {
      component.showComparison([
        { containerSerial: "C-1", templateName: "base", equal: false, missing: ["hotp"], additional: ["totp"] },
        { containerSerial: "C-2", templateName: "base", equal: true, missing: [], additional: [] },
        { containerSerial: "C-3", templateName: "", equal: null, missing: [], additional: [] }
      ]);
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector("th.mat-column-differences").textContent).toContain("Differences");
      const texts = cellTexts("differences");
      expect(texts[1]).toBe("Equal");
      expect(texts[2]).toBe("");
      expect(texts[3]).toBe("");
      const missing = fixture.nativeElement.querySelector("td.mat-column-differences .highlight-false");
      const additional = fixture.nativeElement.querySelector("td.mat-column-differences .highlight-warning");
      expect(missing.textContent.trim()).toBe("- hotp");
      expect(additional.textContent.trim()).toBe("+ totp");
    });

    it("keeps earlier results when further containers are compared", () => {
      component.showComparison([comparisonOf("C-1")]);
      component.showComparison([comparisonOf("C-2", "other")]);
      fixture.detectChanges();

      expect(cellTexts("differences")).toEqual(["Equal", "Equal", "", ""]);
    });

    it("removes the differences column and the results when the comparison is hidden", () => {
      component.showComparison([comparisonOf("C-1")]);
      fixture.detectChanges();

      component.hideComparison();
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector("th.mat-column-differences")).toBeNull();
      expect(fixture.nativeElement.querySelector("th.mat-column-template")).toBeNull();
      expect(component.comparisonByContainerSerial()).toEqual({});
    });

    describe("re-compare on list change", () => {
      const compareFirst = () => {
        component.showComparison([comparisonOf("C-1")]);
        fixture.detectChanges();
        expect(fixture.nativeElement.querySelector("th.mat-column-differences")).not.toBeNull();
        containerService.compareContainersWithTemplates.mockClear();
      };

      const triggers: { name: string; trigger: () => void }[] = [
        { name: "the page index", trigger: () => containerService.pageIndex.set(1) },
        { name: "the sort", trigger: () => containerService.sort.set({ active: "type", direction: "desc" }) },
        {
          name: "the active filter",
          trigger: () => containerService.activeFilter.set(new FilterValue({ value: "type: smartphone" }))
        },
        { name: "the page size at page index 0", trigger: () => containerService.pageSize.set(25) }
      ];

      it.each(triggers)("compares the new list again after it loaded when $name changes", async ({ trigger }) => {
        compareFirst();
        containerService.compareContainersWithTemplates.mockResolvedValue([comparisonOf("C-9")]);
        const newRows = MockPiResponse.fromValue({ count: 1, containers: [containerWithSerial("C-9", "base")] });

        containerService.containerResource.isLoading.set(true);
        trigger();
        fixture.detectChanges();
        // Still loading, so the old rows must not be compared.
        expect(containerService.compareContainersWithTemplates).not.toHaveBeenCalled();

        containerService.containerResource.set(newRows);
        fixture.detectChanges();
        await fixture.whenStable();

        expect(containerService.compareContainersWithTemplates).toHaveBeenCalledTimes(1);
        expect(containerService.compareContainersWithTemplates).toHaveBeenCalledWith(
          newRows.result?.value?.containers
        );
        expect(component.comparisonVisible()).toBe(true);
        expect(Object.keys(component.comparisonByContainerSerial())).toEqual(["C-9"]);
      });

      it("keeps the comparison when the container resource only reloads", () => {
        compareFirst();
        containerService.containerResource.set(fourContainers());
        fixture.detectChanges();

        expect(component.comparisonVisible()).toBe(true);
        expect(component.comparisonByContainerSerial()["C-1"]).toBeDefined();
        expect(containerService.compareContainersWithTemplates).not.toHaveBeenCalled();
        expect(fixture.nativeElement.querySelector("th.mat-column-differences")).not.toBeNull();
      });
    });
  });

  it("names the More Filter button in a tooltip", () => {
    grantRights(["container_list"]);
    containerService.containerResource.set(
      MockPiResponse.fromValue({
        count: 1,
        containers: [{ serial: "C-1", states: [], realms: [], tokens: [], type: "generic", description: "", users: [] }]
      })
    );
    fixture.detectChanges();

    const moreFilter = fixture.debugElement.query(By.css('button[aria-label="More Filter"]'));
    expect(moreFilter.injector.get(MatTooltip, null)?.message).toBe("More Filter");
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
    const rows: {
      name: string;
      initial: string;
      selection: "with-template" | "without-template" | "specific" | "all";
      template?: string;
      expected: string | null;
      keepsType: boolean;
    }[] = [
      { name: "any template", initial: "", selection: "with-template", expected: "any", keepsType: false },
      { name: "no template", initial: "", selection: "without-template", expected: "none", keepsType: false },
      {
        name: "a selected template, clearing previous template conditions",
        initial: "template: none",
        selection: "specific",
        template: "baseline",
        expected: "=baseline",
        keepsType: false
      },
      {
        name: "nothing on Clear Filter, keeping other conditions",
        initial: "template: baseline type: smartphone",
        selection: "all",
        expected: null,
        keepsType: true
      }
    ];

    it.each(rows)("filters for $name", ({ initial, selection, template, expected, keepsType }) => {
      if (initial) {
        containerService.activeFilter.set(new FilterValue({ value: initial }));
      }

      component.onTemplateFilterSelected(selection, template);

      const filter = containerService.activeFilter();
      if (expected === null) {
        expect(filter.hasKey("template")).toBe(false);
      } else {
        expect(filter.getValueOfKey("template")).toBe(expected);
      }
      expect(filter.hasKey("has_template")).toBe(false);
      if (keepsType) {
        expect(filter.hasKey("type")).toBe(true);
      }
    });
  });
});
