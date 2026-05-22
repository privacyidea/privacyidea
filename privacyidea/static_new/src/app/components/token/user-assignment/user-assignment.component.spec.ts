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
import { By } from "@angular/platform-browser";
import { RealmService } from "@services/realm/realm.service";
import { UserData, UserService } from "@services/user/user.service";
import { MockRealmService, MockUserService } from "@testing/mock-services";
import { UserAssignmentComponent } from "./user-assignment.component";

describe("UserAssignmentComponent", () => {
  let component: UserAssignmentComponent;
  let fixture: ComponentFixture<UserAssignmentComponent>;
  let userServiceMock: MockUserService;
  let realmServiceMock: MockRealmService;

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
    realmServiceMock = TestBed.inject(RealmService) as unknown as MockRealmService;
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
    component.onUserFilterInput("user1");
    expect(component.userFilter()).toBe("user1");

    component.onSelectedRealmChange("realm2");
    fixture.detectChanges();

    expect(userServiceMock.selectedUserRealm()).toBe("realm2");
    expect(component.userFilter()).toBe("");
    expect(component.userInputDisabled()).toBe(false);
  });

  it("should disable user filter input if realm is empty", () => {
    component.onSelectedRealmChange("");
    fixture.detectChanges();
    expect(component.userInputDisabled()).toBe(true);

    component.onSelectedRealmChange("realm1");
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
    expect(component.userFilter()).toBe("user1");
  });

  it("should set onlyAddToRealm to false when a user is selected", () => {
    component.onlyAddToRealm.set(true);
    const user: UserData = {
      username: "user1",
      resolver: "",
      description: "",
      editable: false,
      email: "",
      givenname: "",
      mobile: "",
      phone: "",
      surname: "",
      userid: ""
    } as UserData;
    component.onUserSelected(user);
    expect(component.onlyAddToRealm()).toBe(false);
    expect(component.userFilter()).toBe("user1");
    expect(userServiceMock.selectionFilter()).toEqual(user);
  });

  it("clearUser resets the filter", () => {
    component.onUserFilterInput("user1");
    expect(component.userFilter()).toBe("user1");
    component.clearUser();
    expect(component.userFilter()).toBe("");
    expect(userServiceMock.selectionFilter()).toBe("");
  });

  it("displayUser formats values correctly", () => {
    expect(component.displayUser(null)).toBe("");
    expect(component.displayUser("alice")).toBe("alice");
    expect(component.displayUser({ username: "bob" } as UserData)).toBe("bob");
  });
});
