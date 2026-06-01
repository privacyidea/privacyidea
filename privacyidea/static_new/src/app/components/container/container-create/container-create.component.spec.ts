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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { of, throwError } from "rxjs";

import { HttpClient, provideHttpClient } from "@angular/common/http";
import { signal } from "@angular/core";
import { MatDialog } from "@angular/material/dialog";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ContainerRegistrationCompletedDialogComponent } from "@components/container/container-create/container-registration-completed-dialog/container-registration-completed-dialog.component";
import { ContainerRegistrationCompletedDialogWizardComponent } from "@components/container/container-create/container-registration-completed-dialog/container-registration-completed-dialog.wizard.component";
import { AuthService } from "@services/auth/auth.service";
import { ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { RealmService } from "@services/realm/realm.service";
import { TokenService } from "@services/token/token.service";
import { UserService } from "@services/user/user.service";
import { VersioningService } from "@services/version/version.service";
import {
  MockContainerService,
  MockContainerTemplateService,
  MockContentService,
  MockDialogService,
  MockLocalService,
  MockNotificationService,
  MockRealmService,
  MockTokenService,
  MockUserService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { ContainerCreateComponent } from "./container-create.component";
import { ContainerCreateSelfServiceComponent } from "./container-create.self-service.component";
import { ContainerCreateWizardComponent } from "./container-create.wizard.component";
import { ContainerCreatedDialogWizardComponent } from "./container-created-dialog/container-created-dialog.wizard.component";
import { ContainerTemplateService } from "@services/container-template/container-template.service";

class MockIntersectionObserver {
  observe = jest.fn();
  disconnect = jest.fn();

  constructor(
    private callback: IntersectionObserverCallback,
    private options?: IntersectionObserverInit
  ) {}
}

Object.defineProperty(global, "IntersectionObserver", {
  writable: true,
  configurable: true,
  value: MockIntersectionObserver
});

class IOStub {
  private cb: (entries: IntersectionObserverEntry[]) => void;
  observe = jest.fn();
  disconnect = jest.fn();

  constructor(cb: IntersectionObserverCallback, _opts?: IntersectionObserverInit) {
    void _opts;
    this.cb = (entries: IntersectionObserverEntry[]) => cb(entries, this as unknown as IntersectionObserver);
  }

  trigger(entries: IntersectionObserverEntry[]) {
    this.cb(entries);
  }
}

const lastIOInstances: IOStub[] = [];
Object.defineProperty(global, "IntersectionObserver", {
  configurable: true,
  writable: true,
  value: class extends IOStub {
    constructor(cb: IntersectionObserverCallback, opts?: IntersectionObserverInit) {
      super(cb, opts);
      lastIOInstances.push(this);
    }
  }
});

const dialogOpen = jest.fn(() => ({ afterClosed: () => of(null) }));
const dialogCloseAll = jest.fn();
const matDialogMock = { open: dialogOpen, closeAll: dialogCloseAll };

const snack = jest.fn();
const notificationMock = { success: jest.fn(), error: snack, warning: jest.fn(), handleResourceError: jest.fn() };

const navigateByUrl = jest.fn().mockResolvedValue(true);
const routerMock = { navigateByUrl } as unknown as Router;

describe("ContainerCreateComponent", () => {
  let fixture: ComponentFixture<ContainerCreateComponent>;
  let component: ContainerCreateComponent;

  let containerServiceMock: MockContainerService;
  let userService: MockUserService;
  let authService: MockAuthService;
  let httpClientMock: any;
  let dialogServiceMock: MockDialogService;
  let pendingChangesService: MockPendingChangesService;

  let contentService: MockContentService;

  beforeEach(async () => {
    jest.clearAllMocks();
    httpClientMock = {
      get: jest.fn().mockReturnValue(of(""))
    };
    class DummyVersioningService {}
    await TestBed.configureTestingModule({
      imports: [ContainerCreateComponent],
      providers: [
        provideHttpClient(),
        { provide: MatDialog, useValue: matDialogMock },
        { provide: NotificationService, useValue: notificationMock },
        { provide: Router, useValue: routerMock },
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: ContentService, useClass: MockContentService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: UserService, useClass: MockUserService },
        { provide: HttpClient, useValue: httpClientMock },
        { provide: VersioningService, useClass: DummyVersioningService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: ContainerTemplateService, useClass: MockContainerTemplateService },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerCreateComponent);
    component = fixture.componentInstance;

    containerServiceMock = TestBed.inject(ContainerService) as unknown as MockContainerService;
    userService = TestBed.inject(UserService) as unknown as MockUserService;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    authService.actionAllowed.mockReturnValue(true);
    contentService = TestBed.inject(ContentService) as unknown as MockContentService;
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;

    jest
      .spyOn(containerServiceMock, "createContainer")
      .mockReturnValue(of({ result: { value: { container_serial: "C-001" } } } as any));
    jest.spyOn(containerServiceMock, "pollContainerRolloutState").mockReturnValue(
      of({
        result: { value: { containers: [{ info: { registration_state: "client_wait" } }] } }
      } as any)
    );

    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("creates self service", () => {
    const selfFixture = TestBed.createComponent(ContainerCreateSelfServiceComponent);
    expect(selfFixture.componentInstance).toBeTruthy();
  });

  it("creates wizard", () => {
    const wizardFixture = TestBed.createComponent(ContainerCreateWizardComponent);
    expect(wizardFixture.componentInstance).toBeTruthy();
  });

  it("non-QR create: navigates and sets containerSerial", () => {
    containerServiceMock.selectedContainerType.set({ containerType: "generic", description: "", token_types: [] });

    const regSpy = jest.spyOn(component as any, "registerContainer");

    component.createContainer();

    expect(containerServiceMock.createContainer).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "generic",
        description: "",
        user: userService.selectionUsernameFilter()
      })
    );
    expect(regSpy).not.toHaveBeenCalled();
    expect(navigateByUrl).toHaveBeenCalledWith(expect.stringMatching("/containers/details/C-001"));
    expect(containerServiceMock.containerSerial()).toBe("C-001");
  });

  it("shows snack if createContainer returns no serial", () => {
    containerServiceMock.selectedContainerType.set({ containerType: "generic", description: "", token_types: [] });
    (containerServiceMock.createContainer as jest.Mock).mockReturnValueOnce(of({ result: { value: {} } } as any));

    component.createContainer();

    expect(snack).toHaveBeenCalledWith("Container creation failed. No container serial returned.");
    expect(navigateByUrl).not.toHaveBeenCalled();
  });

  it("QR path (smartphone): calls registerContainer", async () => {
    containerServiceMock.selectedContainerType.set({ containerType: "smartphone", description: "", token_types: [] });

    fixture.detectChanges();

    const regSpy = jest.spyOn(component as any, "registerContainer");
    component.createContainer();

    expect(containerServiceMock.createContainer).toHaveBeenCalled();
    expect(regSpy).toHaveBeenCalledWith("C-001");
  });

  it("registerContainer: sets containerSerial signal before opening dialog", () => {
    (component as any).registrationConfigComponent = {
      userStorePassphrase: signal(false),
      passphraseResponse: signal(""),
      passphrasePrompt: signal("")
    };

    let serialAtDialogOpen = "";
    jest.spyOn(component as any, "openRegistrationDialog").mockImplementation(() => {
      serialAtDialogOpen = containerServiceMock.containerSerial();
    });

    (component as any).registerContainer("C-SET-SERIAL");

    expect(serialAtDialogOpen).toBe("C-SET-SERIAL");
  });

  it("registerContainer: stores response, opens dialog, and starts polling", () => {
    const pollSpy = jest.spyOn(containerServiceMock, "startPolling");
    const openDialogSpy = jest.spyOn(dialogServiceMock, "openDialog");

    (component as any).registrationConfigComponent = {
      userStorePassphrase: signal(false),
      passphraseResponse: signal(""),
      passphrasePrompt: signal("")
    };

    (component as any).registerContainer("C-001");
    fixture.detectChanges();

    expect(containerServiceMock.registerContainer).toHaveBeenCalledWith({
      container_serial: "C-001",
      passphrase_user: false,
      passphrase_response: "",
      passphrase_prompt: ""
    });
    expect(openDialogSpy).toHaveBeenCalled();
    expect(pollSpy).toHaveBeenCalledWith("C-001");
  });

  it("reopenEnrollmentDialog opens dialog and polls again", () => {
    (component as any).registerResponse.set({ result: { value: {} } } as any);
    containerServiceMock.containerSerial.set("CONT-42");

    const openDialogSpy = jest.spyOn(dialogServiceMock, "openDialog");
    const pollSpy = jest.spyOn(containerServiceMock, "startPolling");

    component.reopenEnrollmentDialog();
    fixture.detectChanges();

    expect(openDialogSpy).toHaveBeenCalled();
    expect(pollSpy).toHaveBeenCalledWith("CONT-42");
  });

  it("closing enrollment dialog manually stops polling", () => {
    const stopPollingSpy = jest.spyOn(containerServiceMock, "stopPolling");

    (component as any).registrationConfigComponent = {
      userStorePassphrase: signal(false),
      passphraseResponse: signal(""),
      passphrasePrompt: signal("")
    };

    (component as any).registerContainer("C-001");
    fixture.detectChanges();

    const dialogRef = dialogServiceMock.openDialog.mock.results[0].value;
    dialogRef.close();

    expect(stopPollingSpy).toHaveBeenCalled();
  });

  it("pollContainerRolloutState: closes dialog and opens completed dialog when state === 'registered'", () => {
    const closeAllSpy = jest.spyOn(dialogServiceMock, "closeAllDialogs");
    const openDialogSpy = jest.spyOn(dialogServiceMock, "openDialog");

    containerServiceMock.containerDetail.set({
      serial: "CONT-OK",
      type: "smartphone",
      info: { registration_state: "registered" },
      users: [],
      tokens: [],
      realms: [],
      states: [],
      select: ""
    } as any);

    fixture.detectChanges();

    expect(closeAllSpy).toHaveBeenCalled();
    expect(openDialogSpy).toHaveBeenCalled();

    expect(openDialogSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        component: ContainerRegistrationCompletedDialogComponent,
        data: { containerSerial: "CONT-OK" }
      })
    );
  });

  it("pollContainerRolloutState: keeps dialog open when state == 'client_wait'", () => {
    const dialog = TestBed.inject(MatDialog) as any;
    const closeSpy = jest.spyOn(dialog, "closeAll");
    const openSpy = jest.spyOn(dialog, "open");

    containerServiceMock.containerDetail.set({
      serial: "CONT-WAIT",
      type: "smartphone",
      info: { registration_state: "client_wait" },
      users: [],
      tokens: [],
      realms: [],
      states: [],
      select: ""
    } as any);

    fixture.detectChanges();
    TestBed.tick();

    expect(closeSpy).not.toHaveBeenCalled();
    expect(openSpy).not.toHaveBeenCalled();
  });

  it("smartphone without registration wizard policy does not open registration completed dialog", () => {
    TestBed.createComponent(ContainerCreateWizardComponent).destroy();
    TestBed.createComponent(ContainerCreateSelfServiceComponent).destroy();
    authService.authData.set({
      ...authService.authData()!,
      container_wizard: { ...authService.authData()!.container_wizard, registration: false }
    });

    const dialog = TestBed.inject(MatDialog);
    const registerSpy = jest.spyOn(dialog, "open");
    const stopPollingSpy = jest.spyOn(containerServiceMock, "stopPolling");

    jest.spyOn(containerServiceMock.containerDetailsResource, "value").mockReturnValue({
      result: { value: { containers: [{ type: "smartphone", info: { registration_state: "registered" } }] } }
    } as any);

    containerServiceMock.containerSerial.set("CONT-NO-REG");

    fixture.detectChanges();
    TestBed.tick();

    expect(stopPollingSpy).toHaveBeenCalled();
    expect(registerSpy).not.toHaveBeenCalled();
  });

  it("smartphone with registration wizard policy but without register right does not open registration completed dialog", () => {
    TestBed.createComponent(ContainerCreateWizardComponent).destroy();
    TestBed.createComponent(ContainerCreateSelfServiceComponent).destroy();
    authService.authData.set({
      ...authService.authData()!,
      container_wizard: { ...authService.authData()!.container_wizard, registration: true }
    });
    authService.actionAllowed.mockImplementation((action: string) => action !== "container_register");

    const dialog = TestBed.inject(MatDialog);
    const registerSpy = jest.spyOn(dialog, "open");
    const stopPollingSpy = jest.spyOn(containerServiceMock, "stopPolling");

    jest.spyOn(containerServiceMock.containerDetailsResource, "value").mockReturnValue({
      result: { value: { containers: [{ type: "smartphone", info: { registration_state: "registered" } }] } }
    } as any);

    containerServiceMock.containerSerial.set("CONT-NO-RIGHT");

    fixture.detectChanges();
    TestBed.tick();

    expect(stopPollingSpy).toHaveBeenCalled();
    expect(registerSpy).not.toHaveBeenCalled();
  });

  describe("registerHasChanges", () => {
    let hasChangesFn: () => boolean;

    beforeEach(() => {
      hasChangesFn = (pendingChangesService.registerHasChanges as jest.Mock).mock.calls[0][0] as () => boolean;
    });

    it("returns false when all fields are empty", () => {
      expect(hasChangesFn()).toBe(false);
    });

    it("returns true when description is set", () => {
      component.description.set("my description");
      expect(hasChangesFn()).toBe(true);
    });

    it("returns true when a template is selected", () => {
      component.selectedTemplate.set({ name: "my-template", container_type: "generic", template_options: {} } as any);
      expect(hasChangesFn()).toBe(true);
    });

    it("returns true when a user is selected", () => {
      userService.selectionUsernameFilter.set("testuser");
      expect(hasChangesFn()).toBe(true);
    });
  });

  describe("registerSave / registerValidChanges", () => {
    it("registers validChanges and save callbacks in ngOnInit", () => {
      expect(pendingChangesService.registerValidChanges).toHaveBeenCalled();
      expect(pendingChangesService.registerSave).toHaveBeenCalled();
    });

    it("validChanges reflects component.validInput", () => {
      const fn = (pendingChangesService.registerValidChanges as jest.Mock).mock.calls[0][0] as () => boolean;
      component.validInput = true;
      expect(fn()).toBe(true);
      component.validInput = false;
      expect(fn()).toBe(false);
    });

    it("save returns false when container type is not selected", async () => {
      containerServiceMock.selectedContainerType.set(null as any);
      const fn = (pendingChangesService.registerSave as jest.Mock).mock.calls[0][0] as () => Promise<boolean>;
      const result = await fn();
      expect(result).toBe(false);
      expect(containerServiceMock.createContainer).not.toHaveBeenCalled();
    });

    it("save returns false when validInput is false", async () => {
      containerServiceMock.selectedContainerType.set({ containerType: "generic", description: "", token_types: [] });
      component.validInput = false;
      const fn = (pendingChangesService.registerSave as jest.Mock).mock.calls[0][0] as () => Promise<boolean>;
      const result = await fn();
      expect(result).toBe(false);
      expect(containerServiceMock.createContainer).not.toHaveBeenCalled();
    });

    it("save creates container and returns true on success", async () => {
      containerServiceMock.selectedContainerType.set({ containerType: "generic", description: "", token_types: [] });
      component.validInput = true;
      component.description.set("desc");
      const fn = (pendingChangesService.registerSave as jest.Mock).mock.calls[0][0] as () => Promise<boolean>;
      const result = await fn();
      expect(result).toBe(true);
      expect(containerServiceMock.createContainer).toHaveBeenCalled();
    });

    it("save returns false when createContainer throws", async () => {
      containerServiceMock.selectedContainerType.set({ containerType: "generic", description: "", token_types: [] });
      component.validInput = true;
      (containerServiceMock.createContainer as jest.Mock).mockReturnValueOnce(throwError(() => new Error("fail")));
      const fn = (pendingChangesService.registerSave as jest.Mock).mock.calls[0][0] as () => Promise<boolean>;
      const result = await fn();
      expect(result).toBe(false);
    });
  });

  describe("ngOnDestroy", () => {
    it("clears pending-changes registrations on destroy", () => {
      component.ngOnDestroy();
      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
    });
  });

  describe("wizard", () => {
    let wizardFixture: ComponentFixture<ContainerCreateWizardComponent>;
    let wizardComponent: ContainerCreateWizardComponent;

    beforeEach(() => {
      wizardFixture = TestBed.createComponent(ContainerCreateWizardComponent);
      wizardComponent = wizardFixture.componentInstance;
    });

    it("show loaded templates if not empty", async () => {
      authService.authData.set({
        ...authService.authData()!,
        container_wizard: { enabled: true, type: "generic", registration: false, template: null }
      });
      httpClientMock.get.mockReturnValueOnce(of("Mock TOP HTML")).mockReturnValueOnce(of("Mock BOTTOM HTML"));
      wizardFixture = TestBed.createComponent(ContainerCreateWizardComponent);
      wizardFixture.detectChanges();
      expect(wizardFixture.nativeElement.textContent).toContain("Mock TOP HTML");
      expect(wizardFixture.nativeElement.textContent).toContain("Mock BOTTOM HTML");
      expect(wizardFixture.nativeElement.textContent).not.toContain("Create Generic Container");
    });

    it("show default content if customization templates are empty", async () => {
      containerServiceMock.selectedContainerType.set({ containerType: "generic", description: "", token_types: [] });
      authService.authData.set({
        ...authService.authData()!,
        container_wizard: { enabled: true, type: "generic", registration: false, template: null }
      });
      wizardFixture.detectChanges();
      expect(wizardFixture.nativeElement.textContent).toContain("Create Generic Container");
    });

    it("container wizard creates smartphone with template and registration", () => {
      authService.authData.set({
        ...authService.authData()!,
        container_wizard: {
          enabled: true,
          type: "smartphone",
          registration: true,
          template: "custom-template"
        }
      });

      contentService.routeUrl.set(ROUTE_PATHS.CONTAINERS_WIZARD);
      containerServiceMock.selectedContainerType.set({ containerType: "smartphone", description: "", token_types: [] });

      const createSpy = jest.spyOn(containerServiceMock, "createContainer");
      const registerSpy = jest.spyOn(containerServiceMock, "registerContainer");

      wizardComponent.createContainer();

      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({ description: "", type: "smartphone", user: "" })
      );
      expect(registerSpy).toHaveBeenCalled();
    });

    it("container wizard does not register smartphone if register right is missing", () => {
      authService.authData.set({
        ...authService.authData()!,
        container_wizard: {
          enabled: true,
          type: "smartphone",
          registration: true,
          template: "custom-template"
        }
      });
      authService.actionAllowed.mockImplementation((action: string) => action !== "container_register");

      contentService.routeUrl.set(ROUTE_PATHS.CONTAINERS_WIZARD);
      containerServiceMock.selectedContainerType.set({ containerType: "smartphone", description: "", token_types: [] });

      const createSpy = jest.spyOn(containerServiceMock, "createContainer");
      const registerSpy = jest.spyOn(containerServiceMock, "registerContainer");

      wizardComponent.createContainer();

      expect(createSpy).toHaveBeenCalled();
      expect(wizardComponent.generateQRCode()).toBe(false);
      expect(registerSpy).not.toHaveBeenCalled();
    });

    it("wizard registerContainer sets containerSerial before openRegistrationDialog is called", () => {
      (wizardComponent as any).registrationConfigComponent = {
        userStorePassphrase: signal(false),
        passphraseResponse: signal(""),
        passphrasePrompt: signal("")
      };

      let serialAtDialogOpen = "";
      jest.spyOn(wizardComponent as any, "openRegistrationDialog").mockImplementation(() => {
        serialAtDialogOpen = containerServiceMock.containerSerial();
      });

      (wizardComponent as any).registerContainer("W-SERIAL");

      expect(serialAtDialogOpen).toBe("W-SERIAL");
    });

    it("container wizard creates generic container without template and without registration", () => {
      containerServiceMock.selectedContainerType.set({ containerType: "generic", description: "", token_types: [] });

      authService.authData.set({
        ...authService.authData()!,
        container_wizard: {
          enabled: true,
          type: "generic",
          registration: false,
          template: null
        }
      });
      contentService.routeUrl.set(ROUTE_PATHS.CONTAINERS_WIZARD);

      const createSpy = jest.spyOn(containerServiceMock, "createContainer");
      const registerSpy = jest.spyOn(containerServiceMock, "registerContainer");

      wizardComponent.createContainer();

      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "generic"
        })
      );

      expect(wizardComponent.generateQRCode()).toBe(false);
      expect(registerSpy).not.toHaveBeenCalled();
    });

    it("container wizard opens create dialog for non-smartphone", () => {
      const openDialogSpy = jest.spyOn(dialogServiceMock, "openDialog");

      authService.authData.set({
        ...authService.authData()!,
        container_wizard: { enabled: true, type: "generic", registration: false, template: null }
      });

      jest
        .spyOn(containerServiceMock, "createContainer")
        .mockReturnValue(of({ result: { value: { container_serial: "CONT-GENERIC" } } } as any));

      containerServiceMock.selectedContainerType.set({ containerType: "generic", description: "", token_types: [] });
      wizardComponent.createContainer();
      wizardFixture.detectChanges();
      expect(openDialogSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          component: ContainerCreatedDialogWizardComponent
        })
      );
    });

    it("smartphone without register policy in wizard opens create dialog", () => {
      authService.actionAllowed.mockImplementation((action: string) => action !== "container_register");
      authService.authData.set({
        ...authService.authData()!,
        container_wizard: { enabled: true, type: "smartphone", registration: false, template: null }
      });

      wizardFixture = TestBed.createComponent(ContainerCreateWizardComponent);
      wizardFixture.detectChanges();

      containerServiceMock.selectedContainerType.set({ containerType: "smartphone", description: "", token_types: [] });

      const openDialogSpy = jest.spyOn(dialogServiceMock, "openDialog");

      wizardFixture.componentInstance.createContainer();

      expect(openDialogSpy).toHaveBeenCalledWith(
        expect.objectContaining({ component: ContainerCreatedDialogWizardComponent })
      );
    });

    it("wizard opens ContainerRegistrationCompletedDialogWizardComponent when registration state is registered", () => {
      authService.authData.set({
        ...authService.authData()!,
        container_wizard: { enabled: true, type: "smartphone", registration: true, template: null }
      });

      wizardFixture = TestBed.createComponent(ContainerCreateWizardComponent);
      wizardFixture.detectChanges();

      const openDialogSpy = jest.spyOn(dialogServiceMock, "openDialog");

      containerServiceMock.containerDetail.set({
        serial: "CONT-WIZARD-DONE",
        type: "smartphone",
        info: { registration_state: "registered" },
        users: [],
        tokens: [],
        realms: [],
        states: [],
        select: ""
      } as any);

      wizardFixture.detectChanges();
      expect(openDialogSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          component: ContainerRegistrationCompletedDialogWizardComponent,
          data: { containerSerial: "CONT-WIZARD-DONE" }
        })
      );
    });
  });
});
