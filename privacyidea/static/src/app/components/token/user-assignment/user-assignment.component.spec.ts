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

import { WritableSignal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatAutocompleteTrigger } from "@angular/material/autocomplete";
import { MatSelect } from "@angular/material/select";
import { By } from "@angular/platform-browser";
import { RealmService } from "@services/realm/realm.service";
import { UserData, UserService } from "@services/user/user.service";
import { MockRealmService, MockUserService } from "@testing/mock-services";
import { ERR } from "@utils/form-rules.utils";
import { UserAssignmentComponent } from "./user-assignment.component";

describe("UserAssignmentComponent", () => {
  let component: UserAssignmentComponent;
  let fixture: ComponentFixture<UserAssignmentComponent>;
  let userServiceMock: MockUserService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserAssignmentComponent],
      providers: [
        { provide: UserService, useClass: MockUserService },
        { provide: RealmService, useClass: MockRealmService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(UserAssignmentComponent);
    userServiceMock = TestBed.inject(UserService) as unknown as MockUserService;
    component = fixture.componentInstance;
    fixture.componentRef.setInput("showOnlyAddToRealm", true);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should disable user filter when onlyAddToRealm is checked", () => {
    userServiceMock.selectedUserRealm.set("realm1");
    fixture.detectChanges();
    expect(component.userInputDisabled()).toBe(false);

    component.onlyAddToRealmChange(true);
    fixture.detectChanges();
    expect(component.onlyAddToRealm()).toBe(true);
    expect(component.userInputDisabled()).toBe(true);

    component.onlyAddToRealmChange(false);
    fixture.detectChanges();
    expect(component.onlyAddToRealm()).toBe(false);
    expect(component.userInputDisabled()).toBe(false);
  });

  it("should toggle onlyAddToRealm via the checkbox click", () => {
    userServiceMock.selectedUserRealm.set("realm1");
    fixture.detectChanges();
    const checkboxDebug = fixture.debugElement.query(By.css("mat-checkbox input[type='checkbox']"));
    expect(checkboxDebug).toBeTruthy();

    expect(component.onlyAddToRealm()).toBe(false);
    expect(component.userInputDisabled()).toBe(false);

    checkboxDebug.nativeElement.click();
    fixture.detectChanges();

    expect(component.onlyAddToRealm()).toBe(true);
    expect(component.userInputDisabled()).toBe(true);

    checkboxDebug.nativeElement.click();
    fixture.detectChanges();

    expect(component.onlyAddToRealm()).toBe(false);
    expect(component.userInputDisabled()).toBe(false);
  });

  it("should clear user filter on realm change", () => {
    component.userFilter.set("user1");

    userServiceMock.selectedUserRealm.set("realm2");
    component.onSelectedRealmChange();
    fixture.detectChanges();

    expect(userServiceMock.selectedUserRealm()).toBe("realm2");
    expect(component.userFilter()).toBe("");
    expect(component.userInputDisabled()).toBe(false);
  });

  it("should disable user filter input if realm is empty", () => {
    userServiceMock.selectedUserRealm.set("");
    component.onSelectedRealmChange();
    fixture.detectChanges();
    expect(component.userInputDisabled()).toBe(true);

    userServiceMock.selectedUserRealm.set("realm1");
    component.onSelectedRealmChange();
    fixture.detectChanges();
    expect(component.userInputDisabled()).toBe(false);
  });

  it("should be disabled initially if no realm is selected", () => {
    fixture = TestBed.createComponent(UserAssignmentComponent);
    component = fixture.componentInstance;
    userServiceMock.selectedUserRealm.set("");
    fixture.detectChanges();

    expect(component.userInputDisabled()).toBe(true);
  });

  it("should set onlyAddToRealm to false when typing in user filter", () => {
    component.onlyAddToRealm.set(true);
    component.onUserFilterInput("user1");
    expect(component.onlyAddToRealm()).toBe(false);
    expect(userServiceMock.selectionFilter()).toBe("user1");
  });

  it("should set onlyAddToRealm to false when a user is selected", () => {
    const user = { username: "user1" } as UserData;
    (userServiceMock.selectionFilteredUsers as WritableSignal<UserData[]>).set([
      user,
      { username: "user2" } as UserData
    ]);
    component.onlyAddToRealm.set(true);
    component.onUserSelected("user1");
    expect(component.onlyAddToRealm()).toBe(false);
    expect(component.userFilter()).toBe("user1");
    expect(userServiceMock.selectionFilter()).toBe(user);
  });

  it("should keep the typed name as the filter for a username missing from the list", () => {
    component.onUserSelected("ghost");
    expect(component.userFilter()).toBe("ghost");
    expect(userServiceMock.selectionFilter()).toBe("ghost");
  });

  it("clearUser resets the filter", () => {
    component.userFilter.set("user1");
    userServiceMock.selectionFilter.set("user1");
    component.clearUser();
    expect(component.userFilter()).toBe("");
    expect(userServiceMock.selectionFilter()).toBe("");
  });

  describe("validation", () => {
    const kinds = (field: () => { errors(): { kind: string }[] }): string[] =>
      field()
        .errors()
        .map((error) => error.kind);

    beforeEach(() => {
      userServiceMock.selectedUserRealm.set("realm1");
    });

    it("is valid and has no errors when not required", () => {
      userServiceMock.selectedUserRealm.set("");
      expect(kinds(component.realmForm)).toEqual([]);
      expect(component.valid()).toBe(true);
    });

    it("requires a realm and a selected user when required", () => {
      fixture.componentRef.setInput("required", true);
      userServiceMock.selectedUserRealm.set("");
      expect(kinds(component.realmForm)).toEqual([ERR.required]);
      expect(component.valid()).toBe(false);

      userServiceMock.selectedUserRealm.set("realm1");
      expect(kinds(component.userFilterForm)).toEqual([ERR.required]);
      expect(component.valid()).toBe(false);

      (userServiceMock.selectedUser as WritableSignal<UserData | null>).set({ username: "user1" } as UserData);
      expect(kinds(component.userFilterForm)).toEqual([]);
      expect(component.valid()).toBe(true);
    });

    it("does not validate the disabled user input when only the realm is added", () => {
      fixture.componentRef.setInput("required", true);
      component.onlyAddToRealmChange(true);
      expect(component.userFilterForm().disabled()).toBe(true);
      expect(component.valid()).toBe(true);
    });

    it("disables the checkbox field while a user name is typed", () => {
      expect(component.onlyAddToRealmForm().disabled()).toBe(false);
      component.userFilter.set("user1");
      expect(component.onlyAddToRealmForm().disabled()).toBe(true);
    });
  });

  describe("template", () => {
    const userInput = (): HTMLInputElement =>
      fixture.debugElement.query(By.css("app-clearable-input input")).nativeElement as HTMLInputElement;

    it("renders the hidden helper inputs through the global class", () => {
      const hidden = fixture.nativeElement.querySelectorAll("input.hidden-input");
      expect(hidden).toHaveLength(2);
      expect(fixture.nativeElement.querySelector("[style]")).toBeNull();
    });

    it("typing in the user input writes the filter and the service selection", () => {
      userServiceMock.selectedUserRealm.set("realm1");
      fixture.detectChanges();
      userInput().value = "ali";
      userInput().dispatchEvent(new Event("input"));
      fixture.detectChanges();
      expect(component.userFilter()).toBe("ali");
      expect(userServiceMock.selectionFilter()).toBe("ali");
    });

    it("picking an option writes the username and hands the user to the service", () => {
      const user = { username: "user1" } as UserData;
      userServiceMock.selectedUserRealm.set("realm1");
      (userServiceMock.selectionFilteredUsers as WritableSignal<UserData[]>).set([
        user,
        { username: "user2" } as UserData
      ]);
      fixture.detectChanges();
      const trigger = fixture.debugElement
        .query(By.directive(MatAutocompleteTrigger))
        .injector.get(MatAutocompleteTrigger);
      trigger.openPanel();
      fixture.detectChanges();
      (document.querySelector("mat-option") as HTMLElement).click();
      fixture.detectChanges();
      expect(userInput().value).toBe("user1");
      expect(component.userFilter()).toBe("user1");
      expect(userServiceMock.selectionFilter()).toBe(user);
    });

    it("the clear button empties the user input", () => {
      userServiceMock.selectedUserRealm.set("realm1");
      component.userFilter.set("user1");
      userServiceMock.selectionFilter.set("user1");
      fixture.detectChanges();
      (fixture.nativeElement.querySelector("app-clear-button button") as HTMLElement).click();
      fixture.detectChanges();
      expect(component.userFilter()).toBe("");
      expect(userServiceMock.selectionFilter()).toBe("");
      expect(userInput().value).toBe("");
    });

    it("disables the user input without a realm and enables it with one", () => {
      userServiceMock.selectedUserRealm.set("");
      fixture.detectChanges();
      expect(userInput().disabled).toBe(true);
      userServiceMock.selectedUserRealm.set("realm1");
      fixture.detectChanges();
      expect(userInput().disabled).toBe(false);
    });

    it("follows a reset of the service realm in the select", async () => {
      const realmService = TestBed.inject(RealmService) as unknown as MockRealmService;
      realmService.realmOptions.set(["realm1", "realm2"]);
      userServiceMock.selectedUserRealm.set("realm2");
      fixture.detectChanges();
      await fixture.whenStable();
      const select = fixture.debugElement.query(By.directive(MatSelect)).componentInstance as MatSelect;
      expect(select.value).toBe("realm2");

      userServiceMock.selectedUserRealm.set("realm1");
      fixture.detectChanges();
      await fixture.whenStable();
      expect(select.value).toBe("realm1");
    });

    it("choosing a realm writes the service signal and clears the user", async () => {
      const realmService = TestBed.inject(RealmService) as unknown as MockRealmService;
      realmService.realmOptions.set(["realm1", "realm2"]);
      userServiceMock.selectedUserRealm.set("realm1");
      component.userFilter.set("user1");
      fixture.detectChanges();
      const select = fixture.debugElement.query(By.directive(MatSelect)).componentInstance as MatSelect;
      select.open();
      fixture.detectChanges();
      (document.querySelectorAll("mat-option")[1] as HTMLElement).click();
      fixture.detectChanges();
      expect(userServiceMock.selectedUserRealm()).toBe("realm2");
      expect(component.userFilter()).toBe("");
    });

    it("renders the required errors once the fields are touched", () => {
      fixture.componentRef.setInput("required", true);
      userServiceMock.selectedUserRealm.set("");
      component.realmForm().markAsTouched();
      fixture.detectChanges();
      expect((fixture.nativeElement as HTMLElement).textContent).toContain("User Realm is required");

      userServiceMock.selectedUserRealm.set("realm1");
      component.userFilterForm().markAsTouched();
      fixture.detectChanges();
      expect((fixture.nativeElement as HTMLElement).textContent).toContain("User is required");
    });
  });
});
