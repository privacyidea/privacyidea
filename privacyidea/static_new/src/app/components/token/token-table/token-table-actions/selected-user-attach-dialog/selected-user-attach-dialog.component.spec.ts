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

import { SelectedUserAssignDialogComponent } from "./selected-user-attach-dialog.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { UserData } from "../../../../../services/user/user.service";

describe("SelectedUserAssignDialogComponent", () => {
  let component: SelectedUserAssignDialogComponent;
  let fixture: ComponentFixture<SelectedUserAssignDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SelectedUserAssignDialogComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MatDialogRef, useValue: { close: jest.fn() } },
        { provide: MAT_DIALOG_DATA, useValue: {} }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SelectedUserAssignDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should close the dialog with null on cancel", () => {
    component.onCancel();
    expect((component as any).dialogRef.close).toHaveBeenCalledWith(null);
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

    component.userFilterControl.setValue(testUser);
    component.selectedUserRealmControl.setValue(testRealm);
    component.pin.set(testPin);
    component.pinRepeat.set(testPin);

    component.onConfirm();

    expect((component as any).dialogRef.close).toHaveBeenCalledWith({
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
    component.userFilterControl.setValue(null);
    component.selectedUserRealmControl.setValue(testRealm);
    component.pin.set(testPin);
    component.pinRepeat.set(testPin);
    component.onConfirm();
    expect((component as any).dialogRef.close).not.toHaveBeenCalled();

    // No realm selected
    component.userFilterControl.setValue(testUser);
    component.selectedUserRealmControl.setValue("");
    component.onConfirm();
    expect((component as any).dialogRef.close).not.toHaveBeenCalled();

    // Pins do not match
    component.userFilterControl.setValue(testUser);
    component.selectedUserRealmControl.setValue(testRealm);
    component.pin.set(testPin);
    component.pinRepeat.set("654321");
    component.onConfirm();
    expect((component as any).dialogRef.close).not.toHaveBeenCalled();
  });
});
