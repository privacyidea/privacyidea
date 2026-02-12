/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { of } from "rxjs";
import { ActivatedRoute, NavigationEnd, Router } from "@angular/router";
import { signal, WritableSignal } from "@angular/core";
import { MatPaginator, PageEvent } from "@angular/material/paginator";
import { MatTableDataSource } from "@angular/material/table";
import { Sort } from "@angular/material/sort";
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from "@angular/material/dialog";

import { ContainerTableComponent } from "./container-table.component";
import { ContainerTableSelfServiceComponent } from "./container-table.self-service.component";

import { AuthService } from "../../../services/auth/auth.service";
import { ContentService } from "../../../services/content/content.service";
import { NotificationService } from "../../../services/notification/notification.service";
import { TableUtilsService } from "../../../services/table-utils/table-utils.service";
import { ContainerDetailData, ContainerService } from "../../../services/container/container.service";

import {
  MockContainerService,
  MockContentService,
  MockLocalService,
  MockNotificationService,
  MockTableUtilsService
} from "../../../../testing/mock-services";
import { MockAuthService } from "../../../../testing/mock-services/mock-auth-service";

function makeResource<T>(initial: T) {
  return {
    value: signal(initial) as WritableSignal<T>,
    reload: jest.fn(),
    error: jest.fn().mockReturnValue(null)
  };
}

describe("ContainerTableComponent (Jest)", () => {
  let component: ContainerTableComponent;
  let fixture: ComponentFixture<ContainerTableComponent>;
  let containerService: MockContainerService;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [ContainerTableComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService },
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

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("containerDataSource maps user_name/user_realm from first user entry", () => {
    const withUsers = {
      result: {
        value: {
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
        }
      }
    } as any;

    (containerService.containerResource as any).set(withUsers);
    fixture.detectChanges();

    const row = component.containerDataSource().data[0] as any;
    expect(row.user_name).toBe("alice");
    expect(row.user_realm).toBe("r1");
  });

  describe("#handleStateClick", () => {
    it("calls toggleActive and reloads data", () => {
      const element = { serial: "CONT-1", states: ["active"], realms: [], tokens: [], type: "", users: [] } as any;
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
      expect(containerService.eventPageSize).toBe(15);
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

  describe("Selection helpers", () => {
    it("toggleAllRows selects *then* clears every row", () => {
      const dataSource = component.containerDataSource();
      expect(dataSource.data.length).toBe(0);

      const containerDetailData0: ContainerDetailData = {
        serial: "CONT-1",
        states: [],
        realms: [],
        tokens: [],
        type: "",
        users: []
      };
      const containerDetailData1 = { ...containerDetailData0, serial: "CONT-2" };
      const containerDetailData2 = { ...containerDetailData0, serial: "CONT-3" };
      const dataSourceFilled: MatTableDataSource<ContainerDetailData, MatPaginator> = new MatTableDataSource([
        containerDetailData0,
        containerDetailData1,
        containerDetailData2
      ]);
      component.containerDataSource.set(dataSourceFilled);

      fixture.detectChanges();
      expect(component.isAllSelected()).toBe(false);
      component.toggleAllRows();
      expect(component.isAllSelected()).toBe(true);
      const elements = component.containerDataSource().data;
      expect(component.containerSelection().length).toBe(elements.length);

      component.toggleAllRows();
      expect(component.isAllSelected()).toBe(false);
      expect(component.containerSelection().length).toBe(0);
    });

    it("toggleRow adds and removes a single row", () => {
      const row = component.containerDataSource().data[0];

      component.toggleRow(row);
      expect(component.containerSelection()).toContain(row);

      component.toggleRow(row);
      expect(component.containerSelection()).not.toContain(row);
    });
  });
});

describe("ContainerTableSelfServiceComponent", () => {
  let component: ContainerTableSelfServiceComponent;
  let fixture: ComponentFixture<ContainerTableSelfServiceComponent>;
  let containerService: MockContainerService;
  let dialogOpen: jest.Mock;

  beforeEach(async () => {
    TestBed.resetTestingModule();

    dialogOpen = jest.fn().mockReturnValue({
      afterClosed: () => of({ confirmed: true }) // default: confirm
    });

    await TestBed.configureTestingModule({
      imports: [ContainerTableSelfServiceComponent, BrowserAnimationsModule, MatDialogModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService },
        { provide: MatDialog, useValue: { open: dialogOpen } },
        { provide: MAT_DIALOG_DATA, useValue: {} },
        { provide: MatDialogRef, useValue: { close: () => {} } },
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

    fixture = TestBed.createComponent(ContainerTableSelfServiceComponent);
    containerService = TestBed.inject(ContainerService) as unknown as MockContainerService;
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => jest.clearAllMocks());

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("exposes the expected self-service columns", () => {
    expect(component.columnKeysSelfService).toEqual(["serial", "type", "states", "description", "delete"]);
  });

  it("deleteContainer opens confirmation dialog, deletes and reloads when confirmed", () => {
    const serial = "CONT-DEL";
    const deleteSpy = jest.spyOn(containerService, "deleteContainer");
    const reloadSpy = jest.spyOn(containerService.containerResource, "reload");

    component.deleteContainer(serial);

    expect(dialogOpen).toHaveBeenCalled();
    expect(deleteSpy).toHaveBeenCalledWith(serial);
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("deleteContainer does nothing when dialog closes with falsy value", () => {
    // Make dialog return false now
    (dialogOpen as jest.Mock).mockReturnValueOnce({ afterClosed: () => of({ confirmed: false }) });

    const serial = "CONT-NOOP";
    const deleteSpy = jest.spyOn(containerService, "deleteContainer");
    const reloadSpy = jest.spyOn(containerService.containerResource, "reload");

    component.deleteContainer(serial);

    expect(dialogOpen).toHaveBeenCalled();
    expect(deleteSpy).not.toHaveBeenCalled();
    expect(reloadSpy).not.toHaveBeenCalled();
  });
});
