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
import { MatAutocompleteTrigger } from "@angular/material/autocomplete";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { MatSelect } from "@angular/material/select";
import { By } from "@angular/platform-browser";
import { AuthService } from "@services/auth/auth.service";
import { RealmService } from "@services/realm/realm.service";
import { TokenDetails, TokenService } from "@services/token/token.service";
import { UserData, UserService } from "@services/user/user.service";
import { MockAuthService, MockRealmService, MockTokenService, MockUserService } from "@testing/mock-services";
import { ERR } from "@utils/form-rules.utils";
import { SelectedUserAssignDialogComponent } from "./selected-user-attach-dialog.component";

const testUser = { username: "testuser" } as UserData;

describe("SelectedUserAssignDialogComponent", () => {
  let component: SelectedUserAssignDialogComponent;
  let fixture: ComponentFixture<SelectedUserAssignDialogComponent>;
  let userService: MockUserService;
  let authService: MockAuthService;
  let realmService: MockRealmService;

  const kinds = (field: () => { errors(): { kind: string }[] }): string[] =>
    field()
      .errors()
      .map((error) => error.kind);

  const createComponent = (setPinAllowed: boolean): void => {
    authService.actionAllowed.mockImplementation((action: string) => setPinAllowed && action === "setpin");
    fixture = TestBed.createComponent(SelectedUserAssignDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  };

  const fillValid = (): void => {
    component.selectedUser.set(testUser);
    component.model.set({ realm: "testrealm", userText: "testuser", pin: "123456", pinRepeat: "123456" });
  };

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
        { provide: RealmService, useClass: MockRealmService },
        { provide: AuthService, useClass: MockAuthService }
      ]
    }).compileComponents();

    userService = TestBed.inject(UserService) as unknown as MockUserService;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    realmService = TestBed.inject(RealmService) as unknown as MockRealmService;
    realmService.realmOptions.set(["testrealm", "otherrealm"]);
    userService.selectedUserRealm.set("testrealm");
    createComponent(true);
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should close the dialog with null on cancel", () => {
    component.onCancel();
    expect(component.dialogRef.close).toHaveBeenCalledWith(null);
  });

  it("starts with the service realm and the service user filter", () => {
    expect(component.model().realm).toBe("testrealm");
    expect(component.model().userText).toBe("");
    expect(component.selectedUser()).toBeNull();
  });

  describe("validation", () => {
    it("requires a realm", () => {
      component.model.update((m) => ({ ...m, realm: "" }));
      expect(kinds(component.form.realm)).toEqual([ERR.required]);
      component.model.update((m) => ({ ...m, realm: "testrealm" }));
      expect(kinds(component.form.realm)).toEqual([]);
    });

    it("requires a user chosen from the list", () => {
      component.model.update((m) => ({ ...m, userText: "typed" }));
      expect(kinds(component.form.userText)).toEqual([ERR.required]);
      component.selectedUser.set(testUser);
      expect(kinds(component.form.userText)).toEqual([]);
    });

    it("reports a PIN mismatch only on the repeated PIN", () => {
      fillValid();
      component.model.update((m) => ({ ...m, pinRepeat: "654321" }));
      expect(kinds(component.form.pinRepeat)).toEqual([ERR.pinMismatch]);
      expect(kinds(component.form.pin)).toEqual([]);
      expect(component.form().valid()).toBe(false);
    });

    it("accepts an empty PIN pair", () => {
      fillValid();
      component.model.update((m) => ({ ...m, pin: "", pinRepeat: "" }));
      expect(component.form().valid()).toBe(true);
    });

    it("ignores a PIN mismatch when setting a PIN is not allowed", () => {
      createComponent(false);
      fillValid();
      component.model.update((m) => ({ ...m, pinRepeat: "other" }));
      expect(kinds(component.form.pinRepeat)).toEqual([]);
      expect(component.form().valid()).toBe(true);
    });
  });

  describe("confirm", () => {
    it("closes the dialog with the username, realm and pin", () => {
      fillValid();
      component.onConfirm();
      expect(component.dialogRef.close).toHaveBeenCalledWith({
        username: "testuser",
        realm: "testrealm",
        pin: "123456"
      });
    });

    it("sends a null pin when no pin is typed", () => {
      fillValid();
      component.model.update((m) => ({ ...m, pin: "", pinRepeat: "" }));
      component.onConfirm();
      expect(component.dialogRef.close).toHaveBeenCalledWith({ username: "testuser", realm: "testrealm", pin: null });
    });

    it("does not close and touches every field when the form is invalid", async () => {
      fillValid();
      component.model.update((m) => ({ ...m, realm: "", pinRepeat: "654321" }));
      component.onConfirm();
      await fixture.whenStable();
      expect(component.dialogRef.close).not.toHaveBeenCalled();
      expect(component.form.realm().touched()).toBe(true);
      expect(component.form.pinRepeat().touched()).toBe(true);
    });

    it("does not close when no user is selected", () => {
      fillValid();
      component.selectedUser.set(null);
      component.onConfirm();
      expect(component.dialogRef.close).not.toHaveBeenCalled();
    });

    it("onAction submit confirms and a null action cancels", () => {
      const confirm = jest.spyOn(component, "onConfirm").mockReturnValue();
      const cancel = jest.spyOn(component, "onCancel").mockReturnValue();
      component.onAction("submit");
      expect(confirm).toHaveBeenCalled();
      component.onAction(null);
      expect(cancel).toHaveBeenCalled();
    });
  });

  describe("primary action", () => {
    it("is disabled until realm, user and matching pins are valid", () => {
      expect(component.actions()[0].disabled).toBe(true);
      fillValid();
      expect(component.actions()[0].disabled).toBe(false);
      component.model.update((m) => ({ ...m, pinRepeat: "b" }));
      expect(component.actions()[0].disabled).toBe(true);
      component.model.update((m) => ({ ...m, pinRepeat: m.pin, realm: "" }));
      expect(component.actions()[0].disabled).toBe(true);
    });
  });

  describe("realm and user filter interactions", () => {
    it("onRealmChange resets user and filter and persists the realm in the user service", () => {
      component.selectedUser.set(testUser);
      component.model.update((m) => ({ ...m, userText: "testuser" }));
      userService.selectionFilter.set("testuser");

      component.model.update((m) => ({ ...m, realm: "otherrealm" }));
      component.onRealmChange();

      expect(userService.selectedUserRealm()).toBe("otherrealm");
      expect(component.selectedUser()).toBeNull();
      expect(component.model().userText).toBe("");
      expect(userService.selectionFilter()).toBe("");
    });

    it("onUserFilterInput forwards the filter and clears the selection when it is empty", () => {
      component.selectedUser.set(testUser);
      component.onUserFilterInput("tes");
      expect(userService.selectionFilter()).toBe("tes");
      expect(component.selectedUser()).toBe(testUser);

      component.onUserFilterInput("");
      expect(component.selectedUser()).toBeNull();
    });

    it("clearUser empties the user text and the selection", () => {
      component.selectedUser.set(testUser);
      component.model.update((m) => ({ ...m, userText: "testuser" }));
      component.clearUser();
      expect(component.model().userText).toBe("");
      expect(component.selectedUser()).toBeNull();
      expect(userService.selectionFilter()).toBe("");
    });

    it("onUserSelected picks the user from the filtered list", () => {
      userService.selectionFilteredUsers.set([testUser]);
      component.onUserSelected("testuser");
      expect(component.selectedUser()).toBe(testUser);
      expect(userService.selectionFilter()).toBe("testuser");
    });

    it("onUserSelected clears the selection for an unknown username", () => {
      component.selectedUser.set(testUser);
      component.onUserSelected("ghost");
      expect(component.selectedUser()).toBeNull();
    });
  });

  describe("template", () => {
    const input = (selector: string): HTMLInputElement =>
      fixture.debugElement.query(By.css(selector)).nativeElement as HTMLInputElement;

    it("typing in the user input writes the model and the service filter", () => {
      const userInput = input("app-clearable-input input");
      userInput.value = "tes";
      userInput.dispatchEvent(new Event("input"));
      fixture.detectChanges();
      expect(component.model().userText).toBe("tes");
      expect(userService.selectionFilter()).toBe("tes");
    });

    it("the clear button empties the user input and the selection", () => {
      component.selectedUser.set(testUser);
      component.model.update((m) => ({ ...m, userText: "testuser" }));
      userService.selectionFilter.set("testuser");
      fixture.detectChanges();
      (fixture.nativeElement.querySelector("app-clear-button button") as HTMLElement).click();
      fixture.detectChanges();
      expect(component.model().userText).toBe("");
      expect(component.selectedUser()).toBeNull();
      expect(input("app-clearable-input input").value).toBe("");
    });

    it("picking an option selects the user", () => {
      userService.selectionFilteredUsers.set([testUser]);
      fixture.detectChanges();
      const trigger = fixture.debugElement
        .query(By.directive(MatAutocompleteTrigger))
        .injector.get(MatAutocompleteTrigger);
      trigger.openPanel();
      fixture.detectChanges();
      (document.querySelector("mat-option") as HTMLElement).click();
      fixture.detectChanges();
      expect(component.selectedUser()).toBe(testUser);
      expect(component.model().userText).toBe("testuser");
    });

    it("choosing a realm in the select writes the model and resets the user", () => {
      component.selectedUser.set(testUser);
      const select = fixture.debugElement.query(By.directive(MatSelect)).componentInstance as MatSelect;
      select.open();
      fixture.detectChanges();
      (document.querySelectorAll("mat-option")[1] as HTMLElement).click();
      fixture.detectChanges();
      expect(component.model().realm).toBe("otherrealm");
      expect(userService.selectedUserRealm()).toBe("otherrealm");
      expect(component.selectedUser()).toBeNull();
    });

    it("renders the realm and user errors once the fields are touched", () => {
      component.model.update((m) => ({ ...m, realm: "" }));
      component.form.realm().markAsTouched();
      component.form.userText().markAsTouched();
      fixture.detectChanges();
      const text = (fixture.nativeElement as HTMLElement).textContent;
      expect(text).toContain("User Realm is required");
      expect(text).toContain("User is required");
    });

    it("typing the PINs updates the model and a mismatch renders the message", () => {
      const [pin, repeat] = Array.from(
        fixture.nativeElement.querySelectorAll("app-masked-input input")
      ) as HTMLInputElement[];
      pin.value = "1234";
      pin.dispatchEvent(new Event("input"));
      repeat.value = "12";
      repeat.dispatchEvent(new Event("input"));
      repeat.dispatchEvent(new Event("blur"));
      fixture.detectChanges();
      expect(component.model().pin).toBe("1234");
      expect(component.model().pinRepeat).toBe("12");
      expect(component.pinMismatchError()).toBe("PINs do not match");
      expect((fixture.nativeElement as HTMLElement).textContent).toContain("PINs do not match");
    });

    it("has no PIN fields when setting a PIN is not allowed", () => {
      createComponent(false);
      expect(fixture.nativeElement.querySelector("app-masked-input")).toBeNull();
    });

    it("warns only when a selected token is already assigned", () => {
      const tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
      expect(fixture.nativeElement.querySelector(".inline-warning")).toBeNull();
      tokenService.setTokenSelection([{ serial: "S1", username: "alice" } as TokenDetails]);
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector(".inline-warning")).not.toBeNull();
    });
  });
});
