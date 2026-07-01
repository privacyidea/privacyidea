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
import { DialogService } from "@services/dialog/dialog.service";
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
import { of } from "rxjs";
import { UserDetailsContainerTableComponent } from "./user-details-container-table.component";

describe("UserDetailsContainerTableComponent", () => {
  let fixture: ComponentFixture<UserDetailsContainerTableComponent>;
  let component: UserDetailsContainerTableComponent;

  let containerServiceMock: MockContainerService;
  let authServiceMock: MockAuthService;
  let userServiceMock: MockUserService;

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
    userServiceMock = TestBed.inject(UserService) as unknown as MockUserService;
    (authServiceMock.actionAllowed as jest.Mock).mockReturnValue(true);

    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => jest.clearAllMocks());

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("has the select column first followed by the data columns", () => {
    expect(component.displayedColumns).toEqual(["select", "serial", "type", "states", "description", "realms"]);
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

  describe("selection", () => {
    const rows: ContainerDetailData[] = [
      { serial: "C-1", states: [] } as unknown as ContainerDetailData,
      { serial: "C-2", states: [] } as unknown as ContainerDetailData
    ];

    beforeEach(() => {
      component.dataSource.data = rows;
    });

    it("toggleAllRows selects and deselects every row", () => {
      component.toggleAllRows();
      expect(component.selection()).toEqual(rows);
      expect(component.isAllSelected()).toBe(true);

      component.toggleAllRows();
      expect(component.selection()).toEqual([]);
      expect(component.isAllSelected()).toBe(false);
    });

    it("toggleRow adds and removes a single row", () => {
      component.toggleRow(rows[0]);
      expect(component.selection()).toEqual([rows[0]]);

      component.toggleRow(rows[0]);
      expect(component.selection()).toEqual([]);
    });

    it("isAllSelected is false when the table is empty", () => {
      component.dataSource.data = [];
      component.selection.set([]);
      expect(component.isAllSelected()).toBe(false);
    });
  });

  describe("deleteSelected", () => {
    const selected: ContainerDetailData[] = [
      { serial: "C-1", states: [] } as unknown as ContainerDetailData,
      { serial: "C-2", states: [] } as unknown as ContainerDetailData
    ];

    function mockDialogResult(result: unknown): void {
      jest
        .spyOn((component as unknown as { dialogService: DialogService }).dialogService, "openDialog")
        .mockReturnValue({ afterClosed: () => of(result) } as ReturnType<DialogService["openDialog"]>);
    }

    it("deletes every selected container and reloads when confirmed", () => {
      component.selection.set(selected);
      mockDialogResult(true);

      component.deleteSelected();

      expect(containerServiceMock.deleteContainer).toHaveBeenCalledWith("C-1");
      expect(containerServiceMock.deleteContainer).toHaveBeenCalledWith("C-2");
      expect(containerServiceMock.userContainersResource.reload).toHaveBeenCalledTimes(1);
    });

    it("does nothing when the confirmation is dismissed", () => {
      component.selection.set(selected);
      mockDialogResult(false);

      component.deleteSelected();

      expect(containerServiceMock.deleteContainer).not.toHaveBeenCalled();
      expect(containerServiceMock.userContainersResource.reload).not.toHaveBeenCalled();
    });
  });

  it("unassignSelected unassigns each container for the current user and reloads", () => {
    userServiceMock.detailsUser.set({ username: "alice", realm: "r1" });
    userServiceMock.selectedUserRealm.set("r1");
    component.selection.set([
      { serial: "C-1", states: [] } as unknown as ContainerDetailData,
      { serial: "C-2", states: [] } as unknown as ContainerDetailData
    ]);

    component.unassignSelected();

    expect(containerServiceMock.unassignUser).toHaveBeenCalledWith("C-1", "alice", "r1");
    expect(containerServiceMock.unassignUser).toHaveBeenCalledWith("C-2", "alice", "r1");
    expect(containerServiceMock.userContainersResource.reload).toHaveBeenCalledTimes(1);
  });

  it("toggleActiveSelected toggles each container and reloads", () => {
    component.selection.set([
      { serial: "C-1", states: ["active"] } as unknown as ContainerDetailData,
      { serial: "C-2", states: ["disabled"] } as unknown as ContainerDetailData
    ]);

    component.toggleActiveSelected();

    expect(containerServiceMock.toggleActive).toHaveBeenCalledWith("C-1", ["active"]);
    expect(containerServiceMock.toggleActive).toHaveBeenCalledWith("C-2", ["disabled"]);
    expect(containerServiceMock.userContainersResource.reload).toHaveBeenCalledTimes(1);
  });
});
