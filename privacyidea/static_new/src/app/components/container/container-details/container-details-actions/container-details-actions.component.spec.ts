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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MAT_DIALOG_DATA, MatDialog, MatDialogRef } from "@angular/material/dialog";
import { NavigationEnd, Router } from "@angular/router";
import { AuthService } from "@services/auth/auth.service";
import {
  ContainerRegisterData,
  ContainerService,
  ContainerUnregisterData
} from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { NotificationService } from "@services/notification/notification.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import {
  MockContainerService,
  MockContentService,
  MockLocalService,
  MockNotificationService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { of, Subject } from "rxjs";
import { ContainerDetailsActionsComponent } from "./container-details-actions.component";

const routerEvents$ = new Subject<NavigationEnd>();
routerEvents$.next(new NavigationEnd(1, "/", "/"));
const routerMock = {
  navigate: jest.fn().mockResolvedValue(true),
  navigateByUrl: jest.fn().mockResolvedValue(true),
  url: "/",
  events: routerEvents$
} as unknown as jest.Mocked<Router>;

describe("ContainerDetailsActionsComponent", () => {
  let component: ContainerDetailsActionsComponent;
  let fixture: ComponentFixture<ContainerDetailsActionsComponent>;
  let mockContainerService: MockContainerService;
  let authServiceMock: MockAuthService;
  let mockNotificationService: MockNotificationService;
  let dialogOpen: jest.Mock;
  let dialogCloseAll: jest.Mock;

  beforeEach(async () => {
    TestBed.resetTestingModule();

    dialogOpen = jest.fn().mockReturnValue({
      afterClosed: () => of({ confirmed: true })
    });
    dialogCloseAll = jest.fn();
    await TestBed.configureTestingModule({
      imports: [ContainerDetailsActionsComponent],
      providers: [
        provideHttpClient(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService },
        { provide: MatDialog, useValue: { open: dialogOpen, closeAll: dialogCloseAll } },
        { provide: MAT_DIALOG_DATA, useValue: {} },
        { provide: MatDialogRef, useClass: MockMatDialogRef },
        { provide: Router, useValue: routerMock },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerDetailsActionsComponent);
    component = fixture.componentInstance;
    mockContainerService = TestBed.inject(ContainerService) as unknown as MockContainerService;
    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    mockNotificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    fixture.componentRef.setInput("containerSerial", "SMPH-1");
    fixture.componentRef.setInput("containerType", "smartphone");
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should render actions if anyActionsAllowed is true", () => {
    authServiceMock.actionAllowed.mockReturnValue(true);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain("Container Actions");
  });

  it("should not render actions if no action is allowed", () => {
    authServiceMock.actionAllowed.mockReturnValue(false);
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).not.toContain("Container Actions");
  });

  it("should call deleteContainer and navigate on success", () => {
    mockContainerService.deleteContainer = jest.fn().mockReturnValue(of({}));
    jest.spyOn(component["router"], "navigateByUrl");
    component.deleteContainer();
    expect(dialogOpen).toHaveBeenCalled();
    expect(mockContainerService.deleteContainer).toHaveBeenCalledWith("SMPH-1");
    expect(component["router"].navigateByUrl).toHaveBeenCalled();
  });

  it("should call openRegisterInitDialog", () => {
    component.openRegisterInitDialog(false);
    expect(dialogOpen).toHaveBeenCalled();
  });

  it("should call registerContainer, open finalize dialog", () => {
    const registerResponse = MockPiResponse.fromValue<ContainerRegisterData>({} as ContainerRegisterData);
    mockContainerService.registerContainer = jest.fn().mockReturnValue(of(registerResponse));
    jest.spyOn(component, "openRegisterFinalizeDialog");
    jest.spyOn(mockContainerService, "startPolling");
    component.registerContainer(false, "", "", false);
    expect(mockContainerService.registerContainer).toHaveBeenCalled();
    expect(component.openRegisterFinalizeDialog).toHaveBeenCalledWith(registerResponse, false);
    expect(mockContainerService.startPolling).toHaveBeenCalledWith("SMPH-1");
  });

  it("should call unregisterContainer and show notification", () => {
    const unregisterResponse = MockPiResponse.fromValue<ContainerUnregisterData>({ success: true });
    mockContainerService.unregister.mockReturnValue(of(unregisterResponse));
    jest.spyOn(mockNotificationService, "success");
    jest.spyOn(mockContainerService.containerDetailsResource, "reload");
    component.unregisterContainer();
    expect(mockContainerService.unregister).toHaveBeenCalledWith("SMPH-1");
    expect(mockNotificationService.success).toHaveBeenCalledWith("Container unregistered successfully.");
    expect(mockContainerService.containerDetailsResource.reload).toHaveBeenCalled();
  });
});
