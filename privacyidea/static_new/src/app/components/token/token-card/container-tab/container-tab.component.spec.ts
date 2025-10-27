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
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { provideNoopAnimations } from "@angular/platform-browser/animations";
import { of } from "rxjs";
import { By } from "@angular/platform-browser";

import { ContainerTabComponent } from "./container-tab.component";
import { ROUTE_PATHS } from "../../../../route_paths";
import { ContainerService } from "../../../../services/container/container.service";
import { ContentService } from "../../../../services/content/content.service";
import { VersioningService } from "../../../../services/version/version.service";
import { AuthService } from "../../../../services/auth/auth.service";
import { MatDialog } from "@angular/material/dialog";
import { ActivatedRoute, Router } from "@angular/router";
import { ConfirmationDialogComponent } from "../../../shared/confirmation-dialog/confirmation-dialog.component";
import {
  MockAuthService,
  MockContainerService,
  MockContentService,
  MockLocalService,
  MockNotificationService
} from "../../../../../testing/mock-services";

describe("ContainerTabComponent", () => {
  let component: ContainerTabComponent;
  let containerService: MockContainerService;
  let contentService: MockContentService;
  let router: jest.Mocked<Router>;
  let dialog: { open: jest.Mock, closeAll: jest.Mock };
  let versioning: { getVersion: jest.Mock };
  let fixture: ComponentFixture<ContainerTabComponent>;
  let authService: MockAuthService;

  beforeEach(async () => {
    router = {
      navigateByUrl: jest.fn()
    } as any;

    dialog = {
      open: jest.fn().mockReturnValue({ afterClosed: () => of(true) }),
      closeAll: jest.fn().mockReturnValue(undefined)
    };

    versioning = {
      getVersion: jest.fn().mockReturnValue("1.2.3")
    };

    await TestBed.configureTestingModule({
      imports: [ContainerTabComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNoopAnimations(),
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({ id: "123" })
          }
        },
        { provide: Router, useValue: router },
        { provide: MatDialog, useValue: dialog },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: ContentService, useClass: MockContentService },
        { provide: VersioningService, useValue: versioning },
        { provide: AuthService, useClass: MockAuthService },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTabComponent);
    component = fixture.componentInstance;

    containerService = TestBed.inject(ContainerService) as any;
    contentService = TestBed.inject(ContentService) as any;
    authService = TestBed.inject(AuthService) as MockAuthService;

    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("ngOnInit should read version from VersioningService", () => {
    expect(versioning.getVersion).toHaveBeenCalled();
    expect(component.version).toBe("1.2.3");
  });

  it("containerIsSelected reflects containerSerial signal", () => {
    expect(component.containerIsSelected()).toBe(true);

    containerService.containerSerial.set("");
    expect(component.containerIsSelected()).toBe(false);

    containerService.containerSerial.set("CONT-42");
    expect(component.containerIsSelected()).toBe(true);
  });

  it("states computed reads from containerDetailResource", () => {
    expect(component.states()).toEqual([]);

    containerService.containerDetailResource.value.update((resp: any) => ({
      ...resp,
      result: {
        ...resp.result,
        value: {
          ...resp.result.value,
          containers: [
            {
              ...resp.result.value.containers[0],
              states: ["active", "locked"]
            }
          ]
        }
      }
    }));

    expect(component.states()).toEqual(["active", "locked"]);
  });

  it("onClickContainerOverview navigates to TOKENS_CONTAINERS", () => {
    component.onClickContainerOverview();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.TOKENS_CONTAINERS);
  });

  it("enrollTokenInContainer marks programmatic change, selects container, and navigates", () => {
    containerService.containerSerial.set("CONT-99");

    component.enrollTokenInContainer();

    expect(contentService.isProgrammaticTabChange()).toBe(true);
    expect(containerService.selectedContainer()).toBe("CONT-99");
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.TOKENS_ENROLLMENT);
  });

  it("toggleActive calls service and reloads container details", () => {
    const reloadSpy = containerService.containerDetailResource.reload as jest.Mock;
    containerService.containerSerial.set("CONT-1");

    containerService.containerDetailResource.value.update((resp: any) => ({
      ...resp,
      result: {
        ...resp.result,
        value: {
          ...resp.result.value,
          containers: [
            {
              ...resp.result.value.containers[0],
              states: ["active"]
            }
          ]
        }
      }
    }));

    component.toggleActive();

    expect(containerService.toggleActive).toHaveBeenCalledWith("CONT-1", ["active"]);
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("deleteContainer opens confirm dialog, deletes, and navigates to TOKENS_CONTAINERS when previousUrl is not details", () => {
    (contentService as any).previousUrl = () => "/home";

    component.deleteContainer();

    expect(dialog.open).toHaveBeenCalledWith(ConfirmationDialogComponent, {
      data: {
        serialList: [containerService.containerSerial()],
        title: "Delete Container",
        type: "container",
        action: "delete",
        numberOfTokens: 1
      }
    });

    expect(containerService.deleteContainer).toHaveBeenCalledWith(containerService.containerSerial());
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.TOKENS_CONTAINERS);
  });

  it("deleteContainer navigates back to previous details page when previousUrl starts with TOKENS_DETAILS", () => {
    const prev = `${ROUTE_PATHS.TOKENS_DETAILS}/X`;
    (contentService as any).previousUrl = () => prev;

    component.deleteContainer();

    expect(containerService.deleteContainer).toHaveBeenCalledWith(containerService.containerSerial());
    expect(contentService.isProgrammaticTabChange()).toBe(true);
    expect(router.navigateByUrl).toHaveBeenCalledWith(prev);
  });

  it("deleteSelectedContainer opens confirm dialog, deletes all, clears selection and reloads list", () => {
    containerService.containerSelection.set([
      { serial: "C-1" } as any,
      { serial: "C-2" } as any
    ]);

    const listReloadSpy = containerService.containerResource.reload as jest.Mock;

    component.deleteSelectedContainer();

    expect(dialog.open).toHaveBeenCalledWith(ConfirmationDialogComponent, {
      data: {
        serialList: ["C-1", "C-2"],
        title: "Delete All Containers",
        type: "container",
        action: "delete",
        numberOfContainers: 2
      }
    });

    expect(containerService.deleteContainer).toHaveBeenCalledTimes(2);
    expect(containerService.deleteContainer).toHaveBeenNthCalledWith(1, "C-1");
    expect(containerService.deleteContainer).toHaveBeenNthCalledWith(2, "C-2");

    expect(containerService.containerSelection()).toEqual([]);
    expect(listReloadSpy).toHaveBeenCalled();
  });

  it("openRegisterInitDialog opens dialog with correct data for register", () => {
    const openSpy = jest.spyOn(dialog, "open");
    component.openRegisterInitDialog(false);
    expect(openSpy).toHaveBeenCalledWith(
      expect.any(Function),
      expect.objectContaining({
        data: expect.objectContaining({
          registerContainer: expect.any(Function),
          rollover: false,
          containerHasOwner: expect.any(Boolean)
        })
      })
    );
  });

  it("openRegisterInitDialog opens dialog with correct data for rollover", () => {
    const openSpy = jest.spyOn(dialog, "open");
    component.openRegisterInitDialog(true);
    expect(openSpy).toHaveBeenCalledWith(
      expect.any(Function),
      expect.objectContaining({
        data: expect.objectContaining({
          registerContainer: expect.any(Function),
          rollover: true,
          containerHasOwner: expect.any(Boolean)
        })
      })
    );
  });

  it("registerContainer calls service and opens finalize dialog, then polls rollout state", () => {
    const registerResponse = {
      result: {
        value: {
          container_url: {
            img: "data:image/123",
            value: "pia://container/..."
          }
        }
      }
    } as any;
    const pollResponse = { result: { value: { containers: [{ info: { registration_state: "registered" } }] } } } as any;
    const registerSpy = jest.spyOn(containerService, "registerContainer").mockReturnValue(of(registerResponse));
    const pollSpy = jest.spyOn(containerService, "pollContainerRolloutState").mockReturnValue(of(pollResponse));
    const openFinalizeSpy = jest.spyOn(component as any, "openRegisterFinalizeDialog");
    const closeAllSpy = jest.spyOn(dialog, "closeAll");

    component.registerContainer(false, "prompt", "response", false);

    expect(registerSpy).toHaveBeenCalledWith({
      container_serial: containerService.containerSerial(),
      passphrase_user: false,
      passphrase_prompt: "prompt",
      passphrase_response: "response",
      rollover: false
    });
    expect(openFinalizeSpy).toHaveBeenCalledWith(registerResponse, false);
    expect(pollSpy).toHaveBeenCalled();
    expect(closeAllSpy).toHaveBeenCalled();
  });

  it("registerContainer with rollover=true passes rollover to service and finalize dialog", () => {
    const registerResponse = { result: { value: { img: "data:image/123", value: "pia://container/..." } } } as any;
    const pollResponse = { result: { value: { containers: [{ info: { registration_state: "registered" } }] } } } as any;
    jest.spyOn(containerService, "registerContainer").mockReturnValue(of(registerResponse));
    jest.spyOn(containerService, "pollContainerRolloutState").mockReturnValue(of(pollResponse));
    const openFinalizeSpy = jest.spyOn(component as any, "openRegisterFinalizeDialog");

    component.registerContainer(false, "prompt", "response", true);

    expect(openFinalizeSpy).toHaveBeenCalledWith(registerResponse, true);
    expect(containerService.registerContainer).toHaveBeenCalledWith(
      expect.objectContaining({ rollover: true })
    );
  });

  it("unregisterContainer calls service, shows notification, and reloads details on success", () => {
    const unregisterResponse = { result: { value: { success: true } } } as any;
    const unregisterSpy = jest.spyOn(containerService, "unregister").mockReturnValue(of(unregisterResponse));
    const notificationSpy = jest.spyOn(component["notificationService"], "openSnackBar");
    const reloadSpy = jest.spyOn(containerService.containerDetailResource, "reload");

    component.unregisterContainer();

    expect(unregisterSpy).toHaveBeenCalledWith(containerService.containerSerial());
    expect(notificationSpy).toHaveBeenCalledWith("Container unregistered successfully.");
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("unregisterContainer shows failure notification if not successful", () => {
    const unregisterResponse = { result: { value: { success: false } } } as any;
    jest.spyOn(containerService, "unregister").mockReturnValue(of(unregisterResponse));
    const notificationSpy = jest.spyOn(component["notificationService"], "openSnackBar");

    component.unregisterContainer();

    expect(notificationSpy).toHaveBeenCalledWith("Failed to unregister container.");
  });

  describe("Registration button visibility and actions", () => {
    function setRoute(url: string) {
      contentService.routeUrl.set(url);
      fixture.detectChanges();
    }

    function setContainerType(type: string) {
      containerService.containerDetailResource.value.update((resp: any) => ({
        ...resp,
        result: {
          ...resp.result,
          value: {
            ...resp.result.value,
            containers: [
              {
                ...resp.result.value.containers[0],
                type
              }
            ]
          }
        }
      }));
      fixture.detectChanges();
    }

    function setRegistrationState(state: string) {
      containerService.containerDetailResource.value.update((resp: any) => ({
        ...resp,
        result: {
          ...resp.result,
          value: {
            ...resp.result.value,
            containers: [
              {
                ...resp.result.value.containers[0],
                info: { registration_state: state }
              }
            ]
          }
        }
      }));
      fixture.detectChanges();
    }

    it("should not display register, unregister, or rollover buttons on overview/list page", () => {
      authService.rights.set(["container_register", "container_unregister", "container_rollover"]);
      setRoute(ROUTE_PATHS.TOKENS_CONTAINERS);
      setContainerType("smartphone");
      setRegistrationState("client_wait");
      fixture.detectChanges();

      const html = fixture.nativeElement as HTMLElement;
      expect(html.textContent).not.toContain("Register");
      expect(html.textContent).not.toContain("Unregister");
      expect(html.textContent).not.toContain("Rollover");
    });

    it("should not display register, unregister, or rollover buttons without rights", () => {
      setRoute(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + "CONT-1");
      setContainerType("smartphone");
      setRegistrationState("client_wait");

      authService.rights.set(["container_unregister", "container_rollover"]);
      fixture.detectChanges();
      let html = fixture.nativeElement as HTMLElement;
      expect(html.textContent).not.toContain("Register");
      expect(html.textContent).toContain("Unregister");
      expect(html.textContent).not.toContain("Rollover");

      authService.rights.set(["container_register", "container_rollover"]);
      fixture.detectChanges();
      html = fixture.nativeElement as HTMLElement;
      expect(html.textContent).toContain("Register");
      expect(html.textContent).not.toContain("Unregister");
      expect(html.textContent).not.toContain("Rollover");

      setRegistrationState("registered");
      authService.rights.set(["container_unregister"]);
      fixture.detectChanges();
      html = fixture.nativeElement as HTMLElement;
      expect(html.textContent).not.toContain("Register");
      expect(html.textContent).toContain("Unregister");
      expect(html.textContent).not.toContain("Rollover");
    });


    it("should show Register button for smartphone, registration_state=client_wait", async () => {
      authService.rights.set(["container_register", "container_unregister", "container_rollover"]);
      setRoute(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + "CONT-1");
      setContainerType("smartphone");
      setRegistrationState("client_wait");
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();

      const html = fixture.nativeElement as HTMLElement;
      expect(html.textContent).toContain("Register");
      expect(html.textContent).not.toContain("Rollover");
      expect(html.textContent).toContain("Unregister");
    });

    it("should show Rollover button for smartphone, registration_state=registered", () => {
      authService.rights.set(["container_register", "container_unregister", "container_rollover"]);
      setRoute(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + "CONT-1");
      setContainerType("smartphone");
      setRegistrationState("registered");
      fixture.detectChanges();

      const html = fixture.nativeElement as HTMLElement;
      expect(html.textContent).not.toContain("Register");
      expect(html.textContent).toContain("Rollover");
      expect(html.textContent).toContain("Unregister");
    });

    it("should show Unregister button for smartphone, registration_state=rollover_completed", () => {
      authService.rights.set(["container_register", "container_unregister", "container_rollover"]);
      setRoute(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + "CONT-1");
      setContainerType("smartphone");
      setRegistrationState("rollover_completed");
      fixture.detectChanges();

      const html = fixture.nativeElement as HTMLElement;
      expect(html.textContent).not.toContain("Register");
      expect(html.textContent).toContain("Rollover");
      expect(html.textContent).toContain("Unregister");
    });

    it("should not show Register/Rollover/Unregister for non-smartphone type", () => {
      authService.rights.set(["container_register", "container_unregister", "container_rollover"]);
      setRoute(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + "CONT-1");
      setContainerType("generic");
      setRegistrationState("client_wait");
      fixture.detectChanges();

      const html = fixture.nativeElement as HTMLElement;
      expect(html.textContent).not.toContain("Register");
      expect(html.textContent).not.toContain("Rollover");
      expect(html.textContent).not.toContain("Unregister");
    });

    it("clicking Register button calls openRegisterInitDialog(false)", () => {
      authService.rights.set(["container_register", "container_unregister", "container_rollover"]);
      setRoute(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + "CONT-1");
      setContainerType("smartphone");
      setRegistrationState("client_wait");
      fixture.detectChanges();

      const spy = jest.spyOn(component, "openRegisterInitDialog");
      const registerBtn: HTMLButtonElement = fixture.debugElement.queryAll(By.css("button"))
        .find(btn => btn.nativeElement.textContent.includes("Register"))?.nativeElement;
      expect(registerBtn).toBeTruthy();
      registerBtn.click();
      expect(spy).toHaveBeenCalledWith(false);
    });

    it("clicking Rollover button calls openRegisterInitDialog(true)", () => {
      authService.rights.set(["container_register", "container_unregister", "container_rollover"]);
      setRoute(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + "CONT-1");
      setContainerType("smartphone");
      setRegistrationState("registered");
      fixture.detectChanges();

      const spy = jest.spyOn(component, "openRegisterInitDialog");
      const rolloverBtn: HTMLButtonElement = fixture.debugElement.queryAll(By.css("button"))
        .find(btn => btn.nativeElement.textContent.includes("Rollover"))?.nativeElement;
      expect(rolloverBtn).toBeTruthy();
      rolloverBtn.click();
      expect(spy).toHaveBeenCalledWith(true);
    });

    it("clicking Unregister button calls unregisterContainer()", () => {
      authService.rights.set(["container_register", "container_unregister", "container_rollover"]);
      setRoute(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + "CONT-1");
      setContainerType("smartphone");
      setRegistrationState("registered");
      fixture.detectChanges();

      const spy = jest.spyOn(component, "unregisterContainer");
      const unregisterBtn: HTMLButtonElement = fixture.debugElement.queryAll(By.css("button"))
        .find(btn => btn.nativeElement.textContent.includes("Unregister"))?.nativeElement;
      expect(unregisterBtn).toBeTruthy();
      unregisterBtn.click();
      expect(spy).toHaveBeenCalled();
    });
  });

  describe("pollContainerRolloutState snackbar notification", () => {
    function createPollResponse(info: Record<string, string>) {
      return {
        id: 0,
        jsonrpc: "",
        detail: {},
        result: {
          status: true,
          value: {
            containers: [
              { info: info, realms: [], serial: "SMPH-123", states: [], tokens: [], type: "smartphone", users: [] }
            ]
          }
        },
        signature: "",
        time: 0,
        version: "",
        versionnumber: ""
      };
    }

    it("should open snackbar with registration success text when registration completes", () => {
      // Arrange
      const pollResponse = createPollResponse({ registration_state: "registered" });

      jest.spyOn(containerService, "pollContainerRolloutState").mockReturnValue(of(pollResponse));
      const notificationSpy = jest.spyOn(component["notificationService"], "openSnackBar");

      // Act
      component["pollContainerRolloutState"](5000, false);

      // Assert
      expect(notificationSpy).toHaveBeenCalledWith("Container registered successfully.");
    });

    it("should open snackbar with rollover success text when rollover completes", () => {
      // Arrange
      const pollResponse = createPollResponse({ registration_state: "registered" });
      jest.spyOn(containerService, "pollContainerRolloutState").mockReturnValue(of(pollResponse));
      const notificationSpy = jest.spyOn(component["notificationService"], "openSnackBar");

      // Act
      component["pollContainerRolloutState"](5000, true);

      // Assert
      expect(notificationSpy).toHaveBeenCalledWith("Container rollover completed successfully.");
    });
  });
});
