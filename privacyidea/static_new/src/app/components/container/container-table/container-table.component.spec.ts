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
        { provide: TokenService, useClass: MockTokenService },
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

  describe("Accessibility labels", () => {
    it("selectRowLabel names the container serial", () => {
      expect((component as unknown as { selectRowLabel: (serial: string) => string }).selectRowLabel("CONT-1")).toBe(
        "Select container CONT-1"
      );
    });

    it("linkLabel appends 'link' to the given label", () => {
      expect((component as unknown as { linkLabel: (label: string) => string }).linkLabel("CONT-1")).toBe(
        "CONT-1 link"
      );
    });
  });
});
