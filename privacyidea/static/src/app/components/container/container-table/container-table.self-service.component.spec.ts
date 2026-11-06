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
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from "@angular/material/dialog";
import { provideRouter } from "@angular/router";
import { AuthService } from "@services/auth/auth.service";
import { ContainerDetailData, ContainerDetails, ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { RealmService } from "@services/realm/realm.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { TokenService } from "@services/token/token.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import {
  MockContainerService,
  MockContentService,
  MockDialogService,
  MockLocalService,
  MockNotificationService,
  MockTableUtilsService,
  MockTokenService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { MockRealmService } from "@testing/mock-services/mock-realm-service";
import { expectsTableStateGating } from "@testing/table-state-gating";
import { Subject } from "rxjs";
import { ContainerTableSelfServiceComponent } from "./container-table.self-service.component";

describe("ContainerTableSelfServiceComponent", () => {
  let component: ContainerTableSelfServiceComponent;
  let fixture: ComponentFixture<ContainerTableSelfServiceComponent>;
  let containerService: MockContainerService;
  let dialogServiceMock: MockDialogService;
  let confirmClosed: Subject<boolean>;

  beforeEach(async () => {
    TestBed.resetTestingModule();

    await TestBed.configureTestingModule({
      imports: [ContainerTableSelfServiceComponent, MatDialogModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: MAT_DIALOG_DATA, useValue: {} },
        { provide: MatDialogRef, useClass: MockMatDialogRef },
        provideRouter([]),
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTableSelfServiceComponent);
    containerService = TestBed.inject(ContainerService) as unknown as MockContainerService;

    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    confirmClosed = new Subject();
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(confirmClosed);
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);

    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => jest.clearAllMocks());

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("links the container serial and its tokens to their details pages", () => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      rights: ["container_list"]
    });
    containerService.containerBelongsToUser.mockReturnValue(true);
    containerService.containerResource.set(
      MockPiResponse.fromValue({
        count: 1,
        containers: [
          {
            serial: "C-1",
            states: [],
            realms: [],
            tokens: [{ serial: "T-1", tokentype: "hotp", container_serial: "C-1" }],
            type: "generic",
            description: "",
            users: []
          } as unknown as ContainerDetailData
        ]
      })
    );
    fixture.detectChanges();
    fixture.nativeElement.querySelector("tr[mat-row]").click();
    fixture.detectChanges();

    const hrefOf = (text: string) =>
      Array.from<HTMLAnchorElement>(fixture.nativeElement.querySelectorAll("a"))
        .find((a) => a.textContent?.trim() === text)
        ?.getAttribute("href");
    expect(hrefOf("C-1")).toBe("/containers/details/C-1");
    expect(hrefOf("T-1")).toBe("/tokens/details/T-1");
  });

  it("toggles the container state with Space", () => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      rights: ["container_list"]
    });
    containerService.containerResource.set(
      MockPiResponse.fromValue({
        count: 1,
        containers: [
          { serial: "C-1", states: ["active"], realms: [], tokens: [], type: "generic", description: "", users: [] }
        ]
      } as unknown as ContainerDetails)
    );
    fixture.detectChanges();
    const handleStateClick = jest.spyOn(component, "handleStateClick").mockImplementation(() => { /* empty */ });
    const space = new KeyboardEvent("keydown", { key: " ", cancelable: true });

    fixture.nativeElement.querySelector("td span[role=button]").dispatchEvent(space);

    expect(handleStateClick).toHaveBeenCalledWith(component.containerDataSource().data[0]);
    expect(space.defaultPrevented).toBe(true);
  });

  it("exposes the expected self-service columns", () => {
    expect(component.columnKeysSelfService).toEqual(["serial", "type", "states", "description", "delete"]);
  });

  it("deleteContainer opens confirmation dialog, deletes and reloads when confirmed", () => {
    const serial = "CONT-DEL";
    const deleteSpy = jest.spyOn(containerService, "deleteContainer");
    const reloadSpy = jest.spyOn(containerService.containerResource, "reload");

    component.deleteContainer(serial);
    confirmClosed.next(true);
    confirmClosed.complete();

    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    expect(deleteSpy).toHaveBeenCalledWith(serial);
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("deleteContainer does nothing when dialog closes with falsy value", () => {
    const serial = "CONT-NOOP";
    const deleteSpy = jest.spyOn(containerService, "deleteContainer");
    const reloadSpy = jest.spyOn(containerService.containerResource, "reload");

    component.deleteContainer(serial);

    confirmClosed.next(false);
    confirmClosed.complete();

    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    expect(deleteSpy).not.toHaveBeenCalled();
    expect(reloadSpy).not.toHaveBeenCalled();
  });

  it("gates the table on its read right, row count and filter", () => {
    expectsTableStateGating({
      state: component.tableState,
      right: "container_list"
    });
  });
});
