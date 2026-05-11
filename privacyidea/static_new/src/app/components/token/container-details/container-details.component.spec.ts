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
import { signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { ActivatedRoute } from "@angular/router";
import { ContainerDetailsComponent } from "@components/token/container-details/container-details.component";
import { ContainerDetailsSelfServiceComponent } from "@components/token/container-details/container-details.self-service.component";
import { TokenDetailsComponent } from "@components/token/token-details/token-details.component";
import { AuditService } from "@services/audit/audit.service";
import { AuthService } from "@services/auth/auth.service";
import { ContainerService, ContainerServiceInterface } from "@services/container/container.service";
import { NotificationService } from "@services/notification/notification.service";
import { TokenService } from "@services/token/token.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";
import { ValidateService } from "@services/validate/validate.service";
import {
  MockAuditService,
  MockContainerService,
  MockNotificationService,
  MockTokenService,
  MockUserService
} from "@testing/mock-services";
import { of } from "rxjs";

class MockValidateService {
  testToken = jest.fn().mockReturnValue(of(null));
}

describe("ContainerDetailsComponent", () => {
  let component: ContainerDetailsComponent;
  let fixture: ComponentFixture<ContainerDetailsComponent>;
  let selfComponent: ContainerDetailsSelfServiceComponent;
  let selfFixture: ComponentFixture<ContainerDetailsSelfServiceComponent>;
  let containerService: ContainerServiceInterface;
  let userService: UserServiceInterface;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TokenDetailsComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({ id: "123" })
          }
        },
        { provide: AuditService, useClass: MockAuditService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: ValidateService, useClass: MockValidateService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: UserService, useClass: MockUserService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerDetailsComponent);
    component = fixture.componentInstance;
    selfFixture = TestBed.createComponent(ContainerDetailsSelfServiceComponent);
    selfComponent = selfFixture.componentInstance;

    component.tokenSerial = signal("Mock serial");
    component.containerSerial = signal("Mock serial");
    component.infoData = signal([
      {
        keyMap: { key: "info", label: "Info" },
        value: { key1: "value1", key2: "value2" },
        isEditing: signal(false)
      }
    ]);
    component.userData = signal([
      {
        keyMap: { key: "user", label: "User" },
        value: "",
        isEditing: signal(false)
      }
    ]);

    containerService = TestBed.inject(ContainerService);
    userService = TestBed.inject(UserService);

    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("creates the component", () => {
    expect(component).toBeTruthy();
  });

  it("creates the self service component", () => {
    expect(selfComponent).toBeTruthy();
  });

  it("addTokenToContainer calls service with correct params", () => {
    component.containerSerial = signal("container1");

    component.addTokenToContainer({
      serial: "Mock Serial",
      tokentype: "hotp",
      active: true,
      username: "username"
    });

    expect(containerService.addTokenToContainer).toHaveBeenCalledWith("container1", "Mock Serial");
  });

  it("toggles realm edit and saves via setContainerRealm()", () => {
    jest.spyOn(containerService, "setContainerRealm").mockReturnValue(of({}));

    component.containerDetailData.set([
      {
        keyMap: { label: "Realms", key: "realms" },
        value: ["realm1"],
        isEditing: signal(false)
      }
    ]);
    const element = component.containerDetailData()[0];

    component.toggleContainerEdit(element);
    expect(element.isEditing()).toBe(true);

    component.selectedRealms.set(["realm1", "realm2"]);
    component.saveContainerEdit(element);

    expect(containerService.setContainerRealm).toHaveBeenCalledWith("Mock serial", ["realm1", "realm2"]);
    expect(element.isEditing()).toBe(false);
  });

  it("edits description and calls setContainerDescription()", () => {
    jest.spyOn(containerService, "setContainerDescription").mockReturnValue(of({}));

    component.containerDetailData.set([
      {
        keyMap: { label: "Description", key: "description" },
        value: "Old description",
        isEditing: signal(false)
      }
    ]);
    const element = component.containerDetailData()[0];

    component.toggleContainerEdit(element);
    expect(element.isEditing()).toBe(true);

    component.containerDetailData.set([
      {
        keyMap: { label: "Description", key: "description" },
        value: "New description from UI",
        isEditing: signal(false)
      }
    ]);

    component.saveContainerEdit(element);
    expect(containerService.setContainerDescription).toHaveBeenCalledWith("Mock serial", "New description from UI");
    expect(element.isEditing()).toBe(false);
  });

  it("enters user edit mode, saves, and exits", () => {
    jest.spyOn(containerService, "assignUser").mockReturnValue(of({}));

    component.userData.set([
      {
        keyMap: { label: "User Name", key: "user_name" },
        value: "",
        isEditing: signal(false)
      }
    ]);
    const element = component.userData()[0];

    expect(component.isEditingUser()).toBe(false);

    component.toggleContainerEdit(element);
    expect(component.isEditingUser()).toBe(true);
    userService.selectedUserRealm.set("realmUser");
    fixture.detectChanges();
    userService.selectionFilter.set("alice");
    fixture.detectChanges();

    component.saveUser();

    expect(containerService.assignUser).toHaveBeenCalledWith({
      containerSerial: "Mock serial",
      username: "alice",
      userRealm: "realmUser"
    });
    expect(component.isEditingUser()).toBe(false);
  });

  it("canceling a realms edit clears selection", () => {
    component.selectedRealms.set(["realm1"]);
    component.containerDetailData.set([
      {
        keyMap: { label: "Realms", key: "realms" },
        value: "irrelevant",
        isEditing: signal(false)
      }
    ]);
    const element = component.containerDetailData()[0];
    component.cancelContainerEdit(element);

    expect(component.selectedRealms()).toEqual([]);
  });

  it("isEditableElement returns true for states when action is allowed", () => {
    const authService = TestBed.inject(AuthService);
    jest.spyOn(authService, "actionAllowed").mockReturnValue(true);
    expect(component.isEditableElement("states")).toBe(true);
  });

  describe("#onStatesChange", () => {
    it("keeps other states when a non-conflicting state is added", () => {
      component.selectedStates.set(["active"]);
      component.onStatesChange(["active", "lost"]);
      expect(component.selectedStates()).toEqual(["active", "lost"]);
    });

    it("removes disabled when active is added", () => {
      component.selectedStates.set(["disabled"]);
      component.onStatesChange(["disabled", "active"]);
      expect(component.selectedStates()).not.toContain("disabled");
      expect(component.selectedStates()).toContain("active");
    });

    it("removes active when disabled is added", () => {
      component.selectedStates.set(["active"]);
      component.onStatesChange(["active", "disabled"]);
      expect(component.selectedStates()).not.toContain("active");
      expect(component.selectedStates()).toContain("disabled");
    });
  });

  it("saveContainerEdit for states calls setStates with selectedStates", () => {
    jest.spyOn(containerService, "setStates").mockReturnValue(of({}));
    component.selectedStates.set(["active", "lost"]);

    component.containerDetailData.set([
      {
        keyMap: { label: "Status", key: "states" },
        value: ["active"],
        isEditing: signal(true)
      }
    ]);
    const element = component.containerDetailData()[0];
    component.saveContainerEdit(element);

    expect(containerService.setStates).toHaveBeenCalledWith("Mock serial", ["active", "lost"]);
    expect(element.isEditing()).toBe(false);
  });

  it("cancelContainerEdit for states resets selectedStates to the original states from containerDetails", () => {
    component.containerDetails.set({
      serial: "Mock serial",
      states: ["active"],
      realms: [],
      tokens: [],
      type: "generic",
      users: []
    });
    component.containerDetailData.set([
      {
        keyMap: { label: "Status", key: "states" },
        value: ["active"],
        isEditing: signal(true)
      }
    ]);
    component.selectedStates.set(["disabled", "lost"]);
    const element = component.containerDetailData()[0];
    component.cancelContainerEdit(element);

    expect(component.selectedStates()).toEqual(["active"]);
    expect(element.isEditing()).toBe(false);
  });

  it("unassignUser triggers service and refresh", () => {
    jest.spyOn(containerService, "unassignUser").mockReturnValue(of({}));

    component.userData.set([
      {
        keyMap: { label: "User Name", key: "user_name" },
        value: "bob",
        isEditing: signal(false)
      },
      {
        keyMap: { label: "User Realm", key: "user_realm" },
        value: "realmUser",
        isEditing: signal(false)
      }
    ]);

    component.unassignUser();

    expect(containerService.unassignUser).toHaveBeenCalledWith("Mock serial", "bob", "realmUser");
  });
});
