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
  let authServiceMock: MockAuthService;

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
    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    (authServiceMock.actionAllowed as jest.Mock).mockReturnValue(true);

    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => jest.clearAllMocks());

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("has the expected data columns plus action columns when rights are granted", () => {
    expect(component.displayedColumns).toEqual([
      "serial",
      "type",
      "states",
      "description",
      "realms",
      "remove",
      "delete"
    ]);
  });

  it("omits action columns when rights are not granted", () => {
    (authServiceMock.actionAllowed as jest.Mock).mockReturnValue(false);
    expect(component.displayedColumns).toEqual(["serial", "type", "states", "description", "realms"]);
  });

  it("wires sort onto the dataSource", () => {
    expect(component.dataSource.sort).toBe(component.sort);
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

  it("unassignUser unassigns the assigned user and reloads", () => {
    const element = {
      serial: "C-456",
      users: [{ user_name: "alice", user_realm: "r1" }]
    } as unknown as ContainerDetailData;
    component.unassignUser(element);
    expect(containerServiceMock.unassignUser).toHaveBeenCalledWith("C-456", "alice", "r1");
    expect(containerServiceMock.userContainersResource.reload).toHaveBeenCalledTimes(1);
  });

  it("unassignUser falls back to top-level user fields", () => {
    const element = {
      serial: "C-789",
      users: [],
      user_name: "bob",
      user_realm: "r2"
    } as unknown as ContainerDetailData;
    component.unassignUser(element);
    expect(containerServiceMock.unassignUser).toHaveBeenCalledWith("C-789", "bob", "r2");
  });

  it("deleteContainer deletes the container and reloads", () => {
    const element = { serial: "C-999" } as unknown as ContainerDetailData;
    component.deleteContainer(element);
    expect(containerServiceMock.deleteContainer).toHaveBeenCalledWith("C-999");
    expect(containerServiceMock.userContainersResource.reload).toHaveBeenCalledTimes(1);
  });
});
