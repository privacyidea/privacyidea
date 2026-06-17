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

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { RealmService } from "@services/realm/realm.service";
import { TokenService } from "@services/token/token.service";
import { UserData, UserService } from "@services/user/user.service";
import { MockRealmService, MockTokenService, MockUserService } from "@testing/mock-services";
import { SelectedUserAssignDialogComponent } from "./selected-user-attach-dialog.component";

describe("SelectedUserAssignDialogComponent", () => {
  let component: SelectedUserAssignDialogComponent;
  let fixture: ComponentFixture<SelectedUserAssignDialogComponent>;
  let userService: MockUserService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SelectedUserAssignDialogComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MatDialogRef, useValue: { close: jest.fn() } },
        { provide: MAT_DIALOG_DATA, useValue: {} },
        { provide: UserService, useClass: MockUserService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: RealmService, useClass: MockRealmService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SelectedUserAssignDialogComponent);
    component = fixture.componentInstance;
    userService = TestBed.inject(UserService) as unknown as MockUserService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should close the dialog with null on cancel", () => {
    component.onCancel();
    expect(component.dialogRef.close).toHaveBeenCalledWith(null);
  });

  it("should toggle pin visibility", () => {
    expect(component.hidePin()).toBe(true);
    component.togglePinVisibility();
    expect(component.hidePin()).toBe(false);
    component.togglePinVisibility();
    expect(component.hidePin()).toBe(true);
  });

  it("should check if pins match", () => {
    component.pin.set("123");
    component.pinRepeat.set("123");
    expect(component.pinsMatch()).toBe(true);
    component.pinRepeat.set("456");
    expect(component.pinsMatch()).toBe(false);
  });

  it("should close the dialog with the correct data on confirm", () => {
    const testUser: UserData = {
      username: "testuser",
      realm: "testrealm",
      user_id: "123",
      description: "",
      editable: false,
      email: "",
      givenname: "",
      mobile: "",
      phone: "",
      resolver: "",
      surname: "",
      userid: ""
    };
    const testRealm = "testrealm";
    const testPin = "123456";

    component.selectedUser.set(testUser);
    component.selectedRealm.set(testRealm);
    component.pin.set(testPin);
    component.pinRepeat.set(testPin);

    component.onConfirm();

    expect(component.dialogRef.close).toHaveBeenCalledWith({
      username: testUser.username,
      realm: testRealm,
      pin: testPin
    });
  });

  it("should not close the dialog on confirm if form is invalid", () => {
    const testUser: UserData = {
      username: "testuser",
      realm: "testrealm",
      user_id: "123",
      description: "",
      editable: false,
      email: "",
      givenname: "",
      mobile: "",
      phone: "",
      resolver: "",
      surname: "",
      userid: ""
    };
    const testRealm = "testrealm";
    const testPin = "123456";

    // No user selected
    component.selectedUser.set(null);
    component.selectedRealm.set(testRealm);
    component.pin.set(testPin);
    component.pinRepeat.set(testPin);
    component.onConfirm();
    expect(component.dialogRef.close).not.toHaveBeenCalled();

    // No realm selected
    component.selectedUser.set(testUser);
    component.selectedRealm.set("");
    component.onConfirm();
    expect(component.dialogRef.close).not.toHaveBeenCalled();

    // Pins do not match
    component.selectedUser.set(testUser);
    component.selectedRealm.set(testRealm);
    component.pin.set(testPin);
    component.pinRepeat.set("654321");
    component.onConfirm();
    expect(component.dialogRef.close).not.toHaveBeenCalled();
  });

  describe("realm and user filter interactions", () => {
    it("onRealmChange should reset user, filter, and persist realm in user service", () => {
      const testUser: UserData = { username: "u1" } as UserData;
      component.selectedUser.set(testUser);
      component.userFilter.set("u1");

      component.onRealmChange("newRealm");

      expect(component.selectedRealm()).toBe("newRealm");
      expect(component.selectedUser()).toBeNull();
      expect(component.userFilter()).toBe("");
      expect(userService.selectedUserRealm()).toBe("newRealm");
    });

    it("onUserFilterInput should clear selectedUser when filter is empty", () => {
      component.selectedUser.set({ username: "u1" } as UserData);
      component.onUserFilterInput("");
      expect(component.selectedUser()).toBeNull();
      expect(component.userFilter()).toBe("");
    });

    it("onUserFilterInput should not clear selection when filter has a value", () => {
      const user = { username: "u1" } as UserData;
      component.selectedUser.set(user);
      component.onUserFilterInput("u");
      expect(component.selectedUser()).toBe(user);
      expect(component.userFilter()).toBe("u");
    });

    it("onUserSelected should set user and sync the filter to the username", () => {
      const user = { username: "alice" } as UserData;
      component.onUserSelected(user);
      expect(component.selectedUser()).toBe(user);
      expect(component.userFilter()).toBe("alice");
    });
  });

  describe("displayUser", () => {
    it("should return empty string for null", () => {
      expect(component.displayUser(null)).toBe("");
    });

    it("should return the string value when given a string", () => {
      expect(component.displayUser("typed")).toBe("typed");
    });

    it("should return the username when given a UserData", () => {
      expect(component.displayUser({ username: "bob" } as UserData)).toBe("bob");
    });
  });

  describe("onAction", () => {
    it("should call onConfirm when value is 'submit'", () => {
      const spy = jest.spyOn(component, "onConfirm").mockReturnValue();
      component.onAction("submit");
      expect(spy).toHaveBeenCalled();
    });

    it("should call onCancel when value is null", () => {
      const spy = jest.spyOn(component, "onCancel").mockReturnValue();
      component.onAction(null);
      expect(spy).toHaveBeenCalled();
    });
  });

  describe("validity computed signals", () => {
    it("realmInvalid should be true when no realm selected", () => {
      component.selectedRealm.set("");
      expect(component.realmInvalid()).toBe(true);
    });

    it("userInvalid should be true when no user selected", () => {
      component.selectedUser.set(null);
      expect(component.userInvalid()).toBe(true);
    });

    it("primary action should be disabled when realm or user invalid or pins do not match", () => {
      component.selectedRealm.set("");
      expect(component.actions()[0].disabled).toBe(true);

      component.selectedRealm.set("realm");
      component.selectedUser.set({ username: "u" } as UserData);
      component.pin.set("a");
      component.pinRepeat.set("a");
      expect(component.actions()[0].disabled).toBe(false);

      component.pinRepeat.set("b");
      expect(component.actions()[0].disabled).toBe(true);
    });
  });
});
