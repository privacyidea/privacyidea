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
import { WritableSignal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { PiResponse } from "@app/app.component";
import { AuthService } from "@services/auth/auth.service";
import { ContainerDetailData, ContainerDetails, ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { UserService } from "@services/user/user.service";
import {
  MockAuthService,
  MockContainerService,
  MockContentService,
  MockLoadingService,
  MockLocalService,
  MockNotificationService,
  MockPiResponse,
  MockTableUtilsService,
  MockUserService
} from "@testing/mock-services";
import { UserDetailsContainerTableComponent } from "./user-details-container-table.component";

describe("UserDetailsContainerTableComponent", () => {
  let fixture: ComponentFixture<UserDetailsContainerTableComponent>;
  let component: UserDetailsContainerTableComponent;

  let containerServiceMock: MockContainerService;

  beforeEach(async () => {
    TestBed.resetTestingModule();

    await TestBed.configureTestingModule({
      imports: [UserDetailsContainerTableComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ContainerService, useClass: MockContainerService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: ContentService, useClass: MockContentService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: UserService, useClass: MockUserService },
        MockLocalService,
        MockNotificationService,
        MockLoadingService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(UserDetailsContainerTableComponent);

    containerServiceMock = TestBed.inject(ContainerService) as unknown as MockContainerService;

    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => jest.clearAllMocks());

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("has the expected displayed columns", () => {
    expect(component.displayedColumns).toEqual(["serial", "type", "states", "description", "realms"]);
  });

  it("exposes pageSizeOptions from TableUtilsService", () => {
    expect(component.pageSizeOptions()).toEqual([5, 10, 25, 50]);
  });

  it("wires paginator and sort in ngAfterViewInit", () => {
    expect(component.dataSource.paginator).toBe(component.paginator);
    expect(component.dataSource.sort).toBe(component.sort);
  });

  it("filterPredicate matches on combined fields", () => {
    const row = {
      serial: "SER-001",
      type: "Box",
      description: "My demo container",
      states: ["active"],
      realms: ["r1", "r2"],
      tokens: [],
      users: [{ user_name: "alice", user_realm: "r1" }]
    } as unknown as ContainerDetailData;

    const pred = component.dataSource.filterPredicate!;
    expect(pred(row, "active")).toBe(true);
    expect(pred(row, "r2")).toBe(true);
    expect(pred(row, "demo")).toBe(true);
    expect(pred(row, "nope")).toBe(false);
  });

  it("handleFilterInput normalises and applies to dataSource.filter", () => {
    const ev = { target: { value: "  MixedCase Text  " } } as unknown as Event;
    component.handleFilterInput(ev);

    expect(component.filterValue).toBe("mixedcase text");
    expect(component.dataSource.filter).toBe("mixedcase text");
  });

  it("onPageSizeChange updates pageSize", () => {
    component.onPageSizeChange(25);
    expect(component.pageSize).toBe(25);
  });

  describe("userContainers signal", () => {
    const mockContainers: ContainerDetailData[] = [
      { serial: "CONT-1", type: "generic", states: [], realms: [], tokens: [], users: [] }
    ];

    it("returns [] on resource error", () => {
      containerServiceMock.userContainersResource.value.set(
        MockPiResponse.fromValue({ containers: mockContainers, count: 1 }) as unknown as PiResponse<ContainerDetails>
      );
      expect(component.userContainers()).toEqual(mockContainers);

      containerServiceMock.userContainersResource.error.set(new Error("network error"));
      expect(component.userContainers()).toEqual([]);
    });

    it("returns [] while loading with no previous containers", () => {
      containerServiceMock.userContainersResource.value.set(undefined);
      (containerServiceMock.userContainersResource.isLoading as WritableSignal<boolean>).set(true);
      expect(component.userContainers()).toEqual([]);
    });

    it("retains previous containers while loading", () => {
      containerServiceMock.userContainersResource.value.set(
        MockPiResponse.fromValue({ containers: mockContainers, count: 1 }) as unknown as PiResponse<ContainerDetails>
      );
      expect(component.userContainers()); // prime previous
      containerServiceMock.userContainersResource.value.set(undefined);
      (containerServiceMock.userContainersResource.isLoading as WritableSignal<boolean>).set(true);
      expect(component.userContainers()).toEqual(mockContainers);
    });

    it("returns containers on successful load", () => {
      containerServiceMock.userContainersResource.value.set(
        MockPiResponse.fromValue({ containers: mockContainers, count: 1 }) as unknown as PiResponse<ContainerDetails>
      );
      expect(component.userContainers()).toEqual(mockContainers);
    });
  });

  it("handleStateClick calls toggleActive and reloads", () => {
    const element = { serial: "C-123", states: ["active"] } as unknown as ContainerDetailData;
    component.handleStateClick(element);
    expect(containerServiceMock.toggleActive).toHaveBeenCalledWith("C-123", ["active"]);
    expect(containerServiceMock.userContainersResource.reload).toHaveBeenCalledTimes(1);
  });
});
