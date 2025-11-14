import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ContainerDetailsActionsComponent } from "./container-details-actions.component";
import {
  MockAuthService,
  MockContainerService,
  MockNotificationService,
  MockContentService,
  MockLocalService
} from "../../../../../testing/mock-services";
import { AuthService } from "../../../../services/auth/auth.service";
import { ContainerService } from "../../../../services/container/container.service";
import { NotificationService } from "../../../../services/notification/notification.service";
import { ContentService } from "../../../../services/content/content.service";
import { MAT_DIALOG_DATA, MatDialog, MatDialogRef } from "@angular/material/dialog";
import { of, Subject } from "rxjs";
import { PiResponse } from "../../../../app.component";
import { provideHttpClient } from "@angular/common/http";
import { NavigationEnd, Router } from "@angular/router";

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
  let mockAuthService: MockAuthService;
  let mockNotificationService: MockNotificationService;
  let dialogOpen: jest.Mock;
  let dialogCloseAll: jest.Mock;

  beforeEach(async () => {
    TestBed.resetTestingModule();

    dialogOpen = jest.fn().mockReturnValue({
      afterClosed: () => of(true)
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
        { provide: MatDialog, useValue: { open: dialogOpen , closeAll: dialogCloseAll} },
        { provide: MAT_DIALOG_DATA, useValue: {} },
        { provide: MatDialogRef, useValue: { close: () => {} } },
        { provide: Router, useValue: routerMock },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerDetailsActionsComponent);
    component = fixture.componentInstance;
    mockContainerService = TestBed.inject(ContainerService) as any;
    mockAuthService = TestBed.inject(AuthService) as any;
    mockNotificationService = TestBed.inject(NotificationService) as any;

    component.containerSerial = "SMPH-1";
    component.containerType = "smartphone";
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should render actions if anyActionsAllowed is true", () => {
    mockAuthService.jwtData.set({...component.authService.jwtData(), rights: ["container_delete"]});
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain("Container Actions");
  });

  it("should not render actions if no action is allowed", () => {
    mockAuthService.jwtData.set({...component.authService.jwtData(), rights: []});
    fixture.detectChanges();
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
    const registerResponse = { result: { value: {} } } as PiResponse<any>;
    mockContainerService.registerContainer = jest.fn().mockReturnValue(of(registerResponse));
    jest.spyOn(component, "openRegisterFinalizeDialog");
    jest.spyOn(mockContainerService, "startPolling");
    component.registerContainer(false, "", "", false);
    expect(mockContainerService.registerContainer).toHaveBeenCalled();
    expect(component.openRegisterFinalizeDialog).toHaveBeenCalledWith(registerResponse, false);
    expect(mockContainerService.startPolling).toHaveBeenCalledWith("SMPH-1");
  });

  it("should call unregisterContainer and show notification", () => {
    const unregisterResponse = { result: { value: { success: true } } } as PiResponse<any>;
    mockContainerService.unregister = jest.fn().mockReturnValue(of(unregisterResponse));
    jest.spyOn(mockNotificationService, "openSnackBar");
    jest.spyOn(mockContainerService.containerDetailResource, "reload");
    component.unregisterContainer();
    expect(mockContainerService.unregister).toHaveBeenCalledWith("SMPH-1");
    expect(mockNotificationService.openSnackBar).toHaveBeenCalledWith("Container unregistered successfully.");
    expect(mockContainerService.containerDetailResource.reload).toHaveBeenCalled();
  });
});
