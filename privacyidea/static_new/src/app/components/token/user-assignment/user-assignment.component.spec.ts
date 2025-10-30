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
import { UserAssignmentComponent } from "./user-assignment.component";
import { FormControl, ReactiveFormsModule } from "@angular/forms";
import { UserData, UserService } from "../../../services/user/user.service";
import { RealmService } from "../../../services/realm/realm.service";
import { MockRealmService, MockUserService } from "../../../../testing/mock-services";


describe("UserAssignmentComponent", () => {
  let component: UserAssignmentComponent;
  let fixture: ComponentFixture<UserAssignmentComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserAssignmentComponent, ReactiveFormsModule],
      providers: [
        { provide: UserService, useClass: MockUserService },
        { provide: RealmService, useClass: MockRealmService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(UserAssignmentComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should use internal controls if inputs not provided", () => {
    expect(component.selectedUserRealmCtrl).toBe(component.internalSelectedUserRealmControl);
    expect(component.userFilterCtrl).toBe(component.internalUserFilterControl);
    expect(component.onlyAddToRealmCtrl).toBe(component.internalOnlyAddToRealmControl);
  });

  it("should bind input controls if provided", () => {
    const realmCtrl = new FormControl<string>("realm2", { nonNullable: true });
    const userCtrl = new FormControl<string | UserData | null>("user1", { nonNullable: true });
    const onlyRealmCtrl = new FormControl<boolean>(true, { nonNullable: true });
    component.selectedUserRealmControl = realmCtrl;
    component.userFilterControl = userCtrl;
    component.onlyAddToRealmControl = onlyRealmCtrl;
    expect(component.selectedUserRealmCtrl).toBe(realmCtrl);
    expect(component.userFilterCtrl).toBe(userCtrl);
    expect(component.onlyAddToRealmCtrl).toBe(onlyRealmCtrl);
  });

  it("should enable/disable controls on value changes", () => {
    const userCtrl = component.userFilterCtrl;
    const onlyRealmCtrl = component.onlyAddToRealmCtrl;
    onlyRealmCtrl.setValue(true);
    expect(userCtrl.disabled).toBe(true);
    onlyRealmCtrl.setValue(false);
    expect(userCtrl.enabled).toBe(true);
  });

  it("should reset user filter on realm change", () => {
    const realmCtrl = component.selectedUserRealmCtrl;
    const userCtrl = component.userFilterCtrl;
    userCtrl.setValue("user1");
    realmCtrl.setValue("realm2");
    expect(userCtrl.value).toBe("");
    expect(userCtrl.enabled).toBe(true);
  });

  it("should disable user filter if realm is empty", () => {
    const realmCtrl = component.selectedUserRealmCtrl;
    const userCtrl = component.userFilterCtrl;
    realmCtrl.setValue("");
    expect(userCtrl.value).toBe("");
    expect(userCtrl.disabled).toBe(true);
    realmCtrl.setValue("realm1");
    expect(userCtrl.enabled).toBe(true);
  });

  it("should set onlyAddToRealm to false and disable when user selected", () => {
    const userCtrl = component.userFilterCtrl;
    const onlyRealmCtrl = component.onlyAddToRealmCtrl;
    userCtrl.setValue("user1");
    expect(onlyRealmCtrl.value).toBe(false);
    expect(onlyRealmCtrl.disabled).toBe(true);
  });

  it("should enable onlyAddToRealm when user is cleared", () => {
    const userCtrl = component.userFilterCtrl;
    const onlyRealmCtrl = component.onlyAddToRealmCtrl;
    userCtrl.setValue("user1");
    userCtrl.setValue(null);
    expect(onlyRealmCtrl.enabled).toBe(true);
  });

  it("onlyAddToRealmControl disables/enables userFilterControl", () => {
    const userCtrl = component.userFilterCtrl;
    const onlyRealmCtrl = component.onlyAddToRealmCtrl;

    onlyRealmCtrl.setValue(true);
    expect(userCtrl.disabled).toBe(true);

    onlyRealmCtrl.setValue(false);
    expect(userCtrl.disabled).toBe(false);
  });
});

