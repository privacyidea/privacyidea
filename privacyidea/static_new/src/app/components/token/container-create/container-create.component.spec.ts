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
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { of } from "rxjs";

import { ContainerCreateComponent } from "./container-create.component";
import { MatDialog } from "@angular/material/dialog";
import { NotificationService } from "../../../services/notification/notification.service";
import { HttpClient, provideHttpClient } from "@angular/common/http";
import {
  MockContainerService,
  MockContentService,
  MockLocalService,
  MockNotificationService,
  MockRealmService,
  MockTokenService,
  MockUserService
} from "../../../../testing/mock-services";
import { Router } from "@angular/router";
import { AuthService } from "../../../services/auth/auth.service";
import { ContainerService } from "../../../services/container/container.service";
import { ContentService } from "../../../services/content/content.service";
import { RealmService } from "../../../services/realm/realm.service";
import { TokenService } from "../../../services/token/token.service";
import { UserService } from "../../../services/user/user.service";
import { VersioningService } from "../../../services/version/version.service";
import { Renderer2, signal } from "@angular/core";
import { ContainerCreateSelfServiceComponent } from "./container-create.self-service.component";
import { ContainerCreateWizardComponent } from "./container-create.wizard.component";
import { ROUTE_PATHS } from "../../../route_paths";
import { MockAuthService } from "../../../../testing/mock-services/mock-auth-service";

class MockIntersectionObserver {
  observe = jest.fn();
  disconnect = jest.fn();

  constructor(
    private callback: any,
    private options?: any
  ) {}
}

Object.defineProperty(global, "IntersectionObserver", {
  writable: true,
  configurable: true,
  value: MockIntersectionObserver
});

class IOStub {
  private cb: (entries: any[]) => void;
  observe = jest.fn();
  disconnect = jest.fn();

  constructor(cb: any, _opts?: any) {
    this.cb = (entries: any[]) => cb(entries, this as any);
  }

  trigger(entries: any[]) {
    this.cb(entries);
  }
}

let lastIO: IOStub | null = null;
Object.defineProperty(global, "IntersectionObserver", {
  configurable: true,
  writable: true,
  value: class extends IOStub {
    constructor(cb: any, opts?: any) {
      super(cb, opts);
      lastIO = this;
    }
  }
});

const dialogOpen = jest.fn(() => ({ afterClosed: () => of(null) }));
const dialogCloseAll = jest.fn();
const matDialogMock = { open: dialogOpen, closeAll: dialogCloseAll };

const snack = jest.fn();
const notificationMock = { openSnackBar: snack };

const navigateByUrl = jest.fn().mockResolvedValue(true);
const routerMock = { navigateByUrl } as unknown as Router;

describe("ContainerCreateComponent", () => {
  let fixture: ComponentFixture<ContainerCreateComponent>;
  let component: ContainerCreateComponent;
  let selfFixture: ComponentFixture<ContainerCreateSelfServiceComponent>;
  let selfComponent: ContainerCreateSelfServiceComponent;
  let wizardFixture: ComponentFixture<ContainerCreateComponent>;
  let wizardComponent: ContainerCreateComponent;

  let containerServiceMock: MockContainerService;
  let userSvc: MockUserService;
  let authService: MockAuthService;
  let httpClientMock: any;

  let contentService: MockContentService;

  beforeEach(async () => {
    jest.clearAllMocks();
    httpClientMock = {
      get: jest.fn().mockReturnValue(of(""))
    };
    let DummyVersioningService;
    await TestBed.configureTestingModule({
      imports: [ContainerCreateComponent, NoopAnimationsModule],
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
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerCreateComponent);
    component = fixture.componentInstance;
    selfFixture = TestBed.createComponent(ContainerCreateSelfServiceComponent);
    selfComponent = selfFixture.componentInstance;
    wizardFixture = TestBed.createComponent(ContainerCreateWizardComponent);
    wizardComponent = wizardFixture.componentInstance;

    containerServiceMock = TestBed.inject(ContainerService) as unknown as MockContainerService;
    userSvc = TestBed.inject(UserService) as unknown as MockUserService;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    contentService = TestBed.inject(ContentService) as unknown as MockContentService;

    jest
      .spyOn(containerServiceMock, "createContainer")
      .mockReturnValue(of({ result: { value: { container_serial: "C-001" } } } as any));
    jest
      .spyOn(containerServiceMock, "registerContainer")
      .mockReturnValue(of({ result: { value: {} }, detail: { info: "registered" } } as any));
    jest.spyOn(containerServiceMock, "pollContainerRolloutState").mockReturnValue(
      of({
        result: { value: { containers: [{ info: { registration_state: "ok" } }] } }
      } as any)
    );

    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("creates self service", () => {
    expect(selfComponent).toBeTruthy();
  });

  it("creates wizard", () => {
    expect(wizardComponent).toBeTruthy();
  });

  it("non-QR create: navigates and sets containerSerial", () => {
    containerServiceMock.selectedContainerType.set({ containerType: "generic", description: "", token_types: [] });

    const regSpy = jest.spyOn(component as any, "registerContainer");

    component.createContainer();

    expect(containerServiceMock.createContainer).toHaveBeenCalledWith(
      expect.objectContaining({
        container_type: "generic",
        description: "",
        user: userSvc.selectionUsernameFilter()
      })
    );
    expect(regSpy).not.toHaveBeenCalled();
    expect(navigateByUrl).toHaveBeenCalledWith(expect.stringMatching("/tokens/containers/details/C-001"));
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

  it("registerContainer: stores response, opens dialog, and starts polling with 5000", () => {
    const pollSpy = jest.spyOn(containerServiceMock, "startPolling");

    (component as any).registrationConfigComponent = {
      passphraseResponse: signal(""),
      passphrasePrompt: signal("")
    };

    (component as any).registerContainer("C-001");

    expect(containerServiceMock.registerContainer).toHaveBeenCalledWith({
      container_serial: "C-001",
      passphrase_user: false,
      passphrase_response: "",
      passphrase_prompt: ""
    });
    expect(matDialogMock.open).toHaveBeenCalled();
    expect(pollSpy).toHaveBeenCalledWith("C-001");
  });

  it("reopenEnrollmentDialog opens dialog and polls again", () => {
    (component as any).registerResponse.set({ result: { value: {} } } as any);
    containerServiceMock.containerSerial.set("CONT-42");

    const pollSpy = jest.spyOn(containerServiceMock, "startPolling");

    component.reopenEnrollmentDialog();

    expect(matDialogMock.open).toHaveBeenCalled();
    expect(pollSpy).toHaveBeenCalledWith("CONT-42");
  });

  it("pollContainerRolloutState: closes dialog and opens completed dialog when state === 'registered'", () => {
    const dialog = TestBed.inject(MatDialog) as unknown as { closeAll: jest.Mock; open: jest.Mock };
    const closeSpy = jest.spyOn(dialog, "closeAll");
    const openSpy = jest.spyOn(dialog, "open");

    const stopPollingSpy = jest.spyOn(containerServiceMock, "stopPolling");

    jest.spyOn(containerServiceMock.containerDetailResource, "value").mockReturnValue({
      result: { value: { containers: [{ info: { registration_state: "registered" } }] } }
    } as any);

    containerServiceMock.containerSerial.set("CONT-OK");

    fixture.detectChanges();
    TestBed.flushEffects();

    expect(closeSpy).toHaveBeenCalled();
    expect(stopPollingSpy).toHaveBeenCalled();

    expect(openSpy).toHaveBeenCalled();
    expect(openSpy.mock.calls[0][1]).toEqual({ data: { containerSerial: "CONT-OK" } });
  });

  it("pollContainerRolloutState: keeps dialog open when state == 'client_wait'", () => {
    const dialog = TestBed.inject(MatDialog) as any;
    const closeSpy = jest.spyOn(dialog, "closeAll");
    const openSpy = jest.spyOn(dialog, "open");
    const stopPollingSpy = jest.spyOn(containerServiceMock, "stopPolling");

    jest.spyOn(containerServiceMock.containerDetailResource, "value").mockReturnValue({
      result: { value: { containers: [{ info: { registration_state: "client_wait" } }] } }
    } as any);

    containerServiceMock.containerSerial.set("CONT-WAIT");

    fixture.detectChanges();
    TestBed.flushEffects();

    expect(closeSpy).not.toHaveBeenCalled();
    expect(openSpy).not.toHaveBeenCalled();
    expect(stopPollingSpy).not.toHaveBeenCalled();
  });

  it("ngAfterViewInit wires IO and toggles sticky class via renderer", () => {
    const host = fixture.nativeElement as HTMLElement;
    host.innerHTML = `
      <div id="scroller">
        <div id="header"></div>
        <div style="height: 200px"></div>
        <div id="sentinel"></div>
      </div>
    `;
    (component as any).scrollContainer = { nativeElement: host.querySelector("#scroller")! };
    (component as any).stickyHeader = { nativeElement: host.querySelector("#header")! };
    (component as any).stickySentinel = { nativeElement: host.querySelector("#sentinel")! };

    const addClass = jest.spyOn((component as any).renderer as Renderer2, "addClass");
    const removeClass = jest.spyOn((component as any).renderer as Renderer2, "removeClass");

    component.ngAfterViewInit();

    expect(lastIO).toBeTruthy();
    expect(lastIO!.observe).toHaveBeenCalled();

    lastIO!.trigger([{ rootBounds: { top: 0 }, boundingClientRect: { top: -1 } } as any]);
    expect(addClass).toHaveBeenCalledWith((component as any).stickyHeader.nativeElement, "is-sticky");

    lastIO!.trigger([{ rootBounds: { top: 0 }, boundingClientRect: { top: 1 } } as any]);
    expect(removeClass).toHaveBeenCalledWith((component as any).stickyHeader.nativeElement, "is-sticky");
  });

  describe("wizard", () => {
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
      // Arrange: set container_wizard data in authService
      authService.authData.set({
        ...authService.authData()!,
        container_wizard: {
          enabled: true,
          type: "smartphone",
          registration: true,
          template: "custom-template"
        }
      });

      contentService.routeUrl.set(ROUTE_PATHS.TOKENS_CONTAINERS_WIZARD);
      containerServiceMock.selectedContainerType.set({ containerType: "smartphone", description: "", token_types: [] });

      // Spy on createContainer of containerSvc
      const createSpy = jest.spyOn(containerServiceMock, "createContainer");
      const registerSpy = jest.spyOn(containerServiceMock, "registerContainer");

      // Act: call createContainer on wizardComponent
      wizardComponent.createContainer();

      // Assert: check that createContainer was called with correct data
      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          container_type: "smartphone",
          template_name: "custom-template"
        })
      );
      // check registration
      expect(wizardComponent.generateQRCode()).toBe(true);
      expect(registerSpy).toHaveBeenCalled();
    });

    it("container wizard creates generic container without template and without registration", () => {
      containerServiceMock.selectedContainerType.set({ containerType: "generic", description: "", token_types: [] });
      // Arrange: set container_wizard data in authService
      authService.authData.set({
        ...authService.authData()!,
        container_wizard: {
          enabled: true,
          type: "generic",
          registration: false,
          template: null
        }
      });
      contentService.routeUrl.set(ROUTE_PATHS.TOKENS_CONTAINERS_WIZARD);

      // Spy on createContainer of containerSvc
      const createSpy = jest.spyOn(containerServiceMock, "createContainer");
      const registerSpy = jest.spyOn(containerServiceMock, "registerContainer");

      // Act: call createContainer on wizardComponent
      wizardComponent.createContainer();

      // Assert: check that createContainer was called with correct data
      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          container_type: "generic"
        })
      );
      // check registration
      expect(wizardComponent.generateQRCode()).toBe(false);
      expect(registerSpy).not.toHaveBeenCalled();
    });
  });
});
