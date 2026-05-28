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
import { ActivatedRoute } from "@angular/router";
import { ContainerDetailsComponent } from "@components/container/container-details/container-details.component";
import { ContainerDetailsSelfServiceComponent } from "@components/container/container-details/container-details.self-service.component";
import { TokenDetailsComponent } from "@components/token/token-details/token-details.component";
import { AuditService } from "@services/audit/audit.service";
import { AuthService } from "@services/auth/auth.service";
import { ContainerService, ContainerServiceInterface } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { RealmService } from "@services/realm/realm.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { TokenService } from "@services/token/token.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";
import { ValidateService } from "@services/validate/validate.service";
import {
  MockAuditService,
  MockContainerService,
  MockContentService,
  MockNotificationService,
  MockRealmService,
  MockTableUtilsService,
  MockTokenService,
  MockUserService
} from "@testing/mock-services";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { of } from "rxjs";

class MockValidateService {
  testToken = jest.fn().mockReturnValue(of(null));
}

describe("ContainerDetailsComponent", () => {
  let component: ContainerDetailsComponent;
  let fixture: ComponentFixture<ContainerDetailsComponent>;
  let containerService: ContainerServiceInterface;
  let userService: UserServiceInterface;
  let pendingChangesService: MockPendingChangesService;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TokenDetailsComponent],
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
        { provide: UserService, useClass: MockUserService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: ContentService, useClass: MockContentService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerDetailsComponent);
    component = fixture.componentInstance;

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
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;

    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("creates the component", () => {
    expect(component).toBeTruthy();
  });

  it("creates the self service component", () => {
    const selfFixture = TestBed.createComponent(ContainerDetailsSelfServiceComponent);
    expect(selfFixture.componentInstance).toBeTruthy();
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

  it("isEditableElement returns true for description when action is allowed", () => {
    const authService = TestBed.inject(AuthService);
    jest.spyOn(authService, "actionAllowed").mockImplementation((action) => action === "container_description");
    expect(component.isEditableElement("description")).toBe(true);
  });

  it("isEditableElement returns true for realms when action is allowed", () => {
    const authService = TestBed.inject(AuthService);
    jest.spyOn(authService, "actionAllowed").mockImplementation((action) => action === "container_realms");
    expect(component.isEditableElement("realms")).toBe(true);
  });

  it("isEditableElement returns false for an unknown key", () => {
    const authService = TestBed.inject(AuthService);
    jest.spyOn(authService, "actionAllowed").mockReturnValue(true);
    expect(component.isEditableElement("unknown")).toBe(false);
  });

  it("cancelContainerEdit for user_name toggles isEditingUser", () => {
    component.userData.set([
      {
        keyMap: { label: "User Name", key: "user_name" },
        value: "alice",
        isEditing: signal(true)
      }
    ]);
    const element = component.userData()[0];
    component.isEditingUser.set(true);

    component.cancelContainerEdit(element);

    expect(component.isEditingUser()).toBe(false);
    expect(element.isEditing()).toBe(false);
  });

  it("cancelContainerEdit for states defaults to [] when containerDetails has no states", () => {
    component.containerDetails.set(undefined as any);
    component.containerDetailData.set([
      {
        keyMap: { label: "Status", key: "states" },
        value: ["active"],
        isEditing: signal(true)
      }
    ]);
    component.selectedStates.set(["disabled"]);
    const element = component.containerDetailData()[0];

    component.cancelContainerEdit(element);

    expect(component.selectedStates()).toEqual([]);
    expect(element.isEditing()).toBe(false);
  });

  it("selectedStates linkedSignal defaults to [] when containerDetails has no states", () => {
    component.containerDetails.set({
      serial: "Mock serial",
      states: undefined as any,
      realms: [],
      tokens: [],
      type: "generic",
      users: []
    });
    expect(component.selectedStates()).toEqual([]);
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

  describe("#saveStates", () => {
    it("returns false, shows an error, and does not call setStates when no state is selected", () => {
      const setStatesSpy = jest.spyOn(containerService, "setStates").mockReturnValue(of({}));
      const notificationService = TestBed.inject(NotificationService);
      component.selectedStates.set([]);

      const result = component.saveStates();

      expect(result).toBe(false);
      expect(notificationService.error).toHaveBeenCalledWith("At least one state must be selected.");
      expect(setStatesSpy).not.toHaveBeenCalled();
    });

    it("returns true and calls setStates when at least one state is selected", () => {
      const setStatesSpy = jest.spyOn(containerService, "setStates").mockReturnValue(of({}));
      component.selectedStates.set(["active"]);

      const result = component.saveStates();

      expect(result).toBe(true);
      expect(setStatesSpy).toHaveBeenCalledWith("Mock serial", ["active"]);
    });
  });

  it("saveContainerEdit for states keeps edit mode open when saveStates fails (empty selection)", () => {
    const setStatesSpy = jest.spyOn(containerService, "setStates").mockReturnValue(of({}));
    const notificationService = TestBed.inject(NotificationService);
    component.selectedStates.set([]);

    component.containerDetailData.set([
      {
        keyMap: { label: "Status", key: "states" },
        value: [],
        isEditing: signal(true)
      }
    ]);
    const element = component.containerDetailData()[0];
    component.saveContainerEdit(element);

    expect(setStatesSpy).not.toHaveBeenCalled();
    expect(notificationService.error).toHaveBeenCalledWith("At least one state must be selected.");
    expect(element.isEditing()).toBe(true);
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

  describe("pending changes", () => {
    it("registers hasChanges in ngOnInit", () => {
      expect(pendingChangesService.registerHasChanges).toHaveBeenCalled();
    });

    it("hasChanges reflects editing state of inline fields", () => {
      const fn = (pendingChangesService.registerHasChanges as jest.Mock).mock.calls[0][0] as () => boolean;
      expect(fn()).toBe(false);

      component.isEditingUser.set(true);
      expect(fn()).toBe(true);
      component.isEditingUser.set(false);

      component.isEditingInfo.set(true);
      expect(fn()).toBe(true);
    });

    it("ngOnDestroy clears all pending-changes registrations", () => {
      component.ngOnDestroy();
      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
    });

    it("registers validChanges and save in ngOnInit", () => {
      expect(pendingChangesService.registerValidChanges).toHaveBeenCalled();
      expect(pendingChangesService.registerSave).toHaveBeenCalled();
    });

    it("saveAllInlineEdits saves every row with isEditing()=true", async () => {
      const editingRow = {
        keyMap: { key: "description", label: "Description" },
        value: "new",
        isEditing: signal(true)
      } as any;
      const idleRow = {
        keyMap: { key: "type", label: "Type" },
        value: "generic",
        isEditing: signal(false)
      } as any;
      (component as any).containerDetailData = () => [editingRow, idleRow];
      const saveSpy = jest.spyOn(component, "saveContainerEdit").mockReturnValue();

      const result = await component.saveAllInlineEdits();

      expect(result).toBe(true);
      expect(saveSpy).toHaveBeenCalledTimes(1);
      expect(saveSpy).toHaveBeenCalledWith(editingRow);
    });

    it("saveAllInlineEdits calls saveUser when isEditingUser", async () => {
      (component as any).containerDetailData = () => [];
      component.isEditingUser.set(true);
      const userSaveSpy = jest.spyOn(component, "saveUser").mockReturnValue();

      await component.saveAllInlineEdits();

      expect(userSaveSpy).toHaveBeenCalled();
    });

    it("saveAllInlineEdits delegates info save to infoChild when isEditingInfo and info exists", async () => {
      (component as any).containerDetailData = () => [];
      const infoEl = {
        keyMap: { key: "info", label: "Information" },
        value: { foo: "bar" },
        isEditing: signal(true)
      } as any;
      (component as any).infoData = () => [infoEl];
      component.isEditingInfo.set(true);
      const infoSaveSpy = jest.fn();
      component.infoChild = { saveInfo: infoSaveSpy } as any;

      await component.saveAllInlineEdits();

      expect(infoSaveSpy).toHaveBeenCalledWith(infoEl);
    });

    it("validChanges always reports true so save button stays enabled", () => {
      const fn = (pendingChangesService.registerValidChanges as jest.Mock).mock.calls[0][0] as () => boolean;
      expect(fn()).toBe(true);
    });

    it("saveAllInlineEdits is a no-op when nothing is in edit mode", async () => {
      (component as any).containerDetailData = () => [];
      (component as any).infoData = () => [];
      component.isEditingUser.set(false);
      component.isEditingInfo.set(false);
      const editSpy = jest.spyOn(component, "saveContainerEdit").mockReturnValue();
      const userSpy = jest.spyOn(component, "saveUser").mockReturnValue();
      component.infoChild = { saveInfo: jest.fn() } as any;

      const result = await component.saveAllInlineEdits();

      expect(result).toBe(true);
      expect(editSpy).not.toHaveBeenCalled();
      expect(userSpy).not.toHaveBeenCalled();
      expect(component.infoChild!.saveInfo).not.toHaveBeenCalled();
    });

    it("saveAllInlineEdits clears isEditingInfo when info element is missing", async () => {
      (component as any).containerDetailData = () => [];
      (component as any).infoData = () => [];
      component.isEditingInfo.set(true);
      const infoSaveSpy = jest.fn();
      component.infoChild = { saveInfo: infoSaveSpy } as any;

      await component.saveAllInlineEdits();

      expect(infoSaveSpy).not.toHaveBeenCalled();
      expect(component.isEditingInfo()).toBe(false);
    });
  });
});
