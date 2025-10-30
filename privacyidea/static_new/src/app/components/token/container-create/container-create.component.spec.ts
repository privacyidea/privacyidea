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
  MockAuthService,
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
import { Renderer2 } from "@angular/core";
import { ContainerCreateSelfServiceComponent } from "./container-create.self-service.component";
import { ContainerCreateWizardComponent } from "./container-create.wizard.component";
import { ROUTE_PATHS } from "../../../route_paths";

class MockIntersectionObserver {
  observe = jest.fn();
  disconnect = jest.fn();

  constructor(private callback: any, private options?: any) {}
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

  let containerSvc: MockContainerService;
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
        { provide: VersioningService, useClass: DummyVersioningService },
        { provide: HttpClient, useValue: httpClientMock },
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

    containerSvc = TestBed.inject(ContainerService) as unknown as MockContainerService;
    userSvc = TestBed.inject(UserService) as unknown as MockUserService;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    contentService = TestBed.inject(ContentService) as unknown as MockContentService;

    jest.spyOn(containerSvc, "createContainer").mockReturnValue(
      of({ result: { value: { container_serial: "C-001" } } } as any)
    );
    jest.spyOn(containerSvc, "registerContainer").mockReturnValue(
      of({ result: { value: {} }, detail: { info: "registered" } } as any)
    );
    jest.spyOn(containerSvc, "pollContainerRolloutState").mockReturnValue(
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
    containerSvc.selectedContainerType.set({ containerType: "generic", description: "", token_types: [] });

    const regSpy = jest.spyOn(component as any, "registerContainer");

    component.createContainer();

    expect(containerSvc.createContainer).toHaveBeenCalledWith(
      expect.objectContaining({
        container_type: "generic",
        description: "",
        template_name: "",
        user: userSvc.selectionUsernameFilter(),
        realm: ""
      })
    );
    expect(regSpy).not.toHaveBeenCalled();
    expect(navigateByUrl).toHaveBeenCalledWith(expect.stringMatching("/tokens/containers/details/C-001"));
    expect(containerSvc.containerSerial()).toBe("C-001");
  });

  it("shows snack if createContainer returns no serial", () => {
    (containerSvc.createContainer as jest.Mock).mockReturnValueOnce(of({ result: { value: {} } } as any));

    component.createContainer();

    expect(snack).toHaveBeenCalledWith("Container creation failed. No container serial returned.");
    expect(navigateByUrl).not.toHaveBeenCalled();
  });

  it("QR path (smartphone): calls registerContainer", () => {
    containerSvc.selectedContainerType.set({ containerType: "smartphone", description: "", token_types: [] });

    fixture.detectChanges();

    const regSpy = jest.spyOn(component as any, "registerContainer");
    component.createContainer();

    expect(containerSvc.createContainer).toHaveBeenCalled();
    expect(regSpy).toHaveBeenCalledWith("C-001");
  });

  it("registerContainer: stores response, opens dialog, and starts polling with 5000", () => {
    const pollSpy = jest.spyOn(containerSvc, "pollContainerRolloutState");

    (component as any).registerContainer("C-001");

    expect(containerSvc.registerContainer).toHaveBeenCalledWith({
      container_serial: "C-001",
      passphrase_response: "",
      passphrase_prompt: ""
    });
    expect(matDialogMock.open).toHaveBeenCalled();
    expect(pollSpy).toHaveBeenCalledWith("C-001", 5000);
  });

  it("reopenEnrollmentDialog opens dialog and polls again (startTime=2000)", () => {
    (component as any).registerResponse.set({ result: { value: {} } } as any);
    containerSvc.containerSerial.set("CONT-42");

    const pollSpy = jest.spyOn(containerSvc, "pollContainerRolloutState");

    component.reopenEnrollmentDialog();

    expect(matDialogMock.open).toHaveBeenCalled();
    expect(pollSpy).toHaveBeenCalledWith("CONT-42", 2000);
  });

  it("pollContainerRolloutState: closes dialog and opens registered dialog when state !== 'client_wait'", () => {
    (containerSvc.pollContainerRolloutState as jest.Mock).mockReturnValueOnce(
      of({
        result: { value: { containers: [{ info: { registration_state: "registered" } }] } }
      } as any)
    );

    (component as any)["pollContainerRolloutState"]("C-9", 1000);

    expect(matDialogMock.closeAll).toHaveBeenCalled();
    expect(matDialogMock.open).toHaveBeenCalled();
  });

  it("pollContainerRolloutState: keeps dialog open when state == 'client_wait'", () => {
    (containerSvc.pollContainerRolloutState as jest.Mock).mockReturnValueOnce(
      of({
        result: { value: { containers: [{ info: { registration_state: "client_wait" } }] } }
      } as any)
    );

    (component as any)["pollContainerRolloutState"]("C-10", 1000);

    expect(matDialogMock.closeAll).not.toHaveBeenCalled();
    expect(navigateByUrl).not.toHaveBeenCalled();
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
        ...authService.authData(),
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
      authService.authData.set({
        ...authService.authData(),
        container_wizard: { enabled: true, type: "generic", registration: false, template: null }
      });
      wizardFixture.detectChanges();
      expect(wizardFixture.nativeElement.textContent).toContain("Create Generic Container");
    });

    it("container wizard creates smartphone with template and registration", () => {
      // Arrange: set container_wizard data in authService
      authService.authData.set({
        ...authService.authData(),
        container_wizard: {
          enabled: true,
          type: "smartphone",
          registration: true,
          template: "custom-template"
        }
      });
      contentService.routeUrl.set(ROUTE_PATHS.TOKENS_CONTAINERS_WIZARD);

      // Spy on createContainer of containerSvc
      const createSpy = jest.spyOn(containerSvc, "createContainer");
      const registerSpy = jest.spyOn(containerSvc, "registerContainer");

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
      // Arrange: set container_wizard data in authService
      authService.authData.set({
        ...authService.authData(),
        container_wizard: {
          enabled: true,
          type: "generic",
          registration: false,
          template: null
        }
      });
      contentService.routeUrl.set(ROUTE_PATHS.TOKENS_CONTAINERS_WIZARD);

      // Spy on createContainer of containerSvc
      const createSpy = jest.spyOn(containerSvc, "createContainer");
      const registerSpy = jest.spyOn(containerSvc, "registerContainer");

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