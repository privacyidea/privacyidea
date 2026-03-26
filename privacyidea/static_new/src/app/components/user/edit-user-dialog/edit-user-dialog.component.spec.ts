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

import { EditUserDialogComponent } from "./edit-user-dialog.component";
import { UserService } from "../../../services/user/user.service";
import { MockUserService } from "../../../../testing/mock-services";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { provideHttpClient } from "@angular/common/http";
import { MockMatDialogRef } from "../../../../testing/mock-mat-dialog-ref";

describe("EditUserDialogComponent", () => {
  let component: EditUserDialogComponent;
  let fixture: ComponentFixture<EditUserDialogComponent>;
  let mockUserService: MockUserService;
  let dialogRefMock: MockMatDialogRef<any, any>;

  const testUserData = {
    username: "edituser",
    resolver: "editresolver",
    email: "edituser@example.com",
    surname: "Edit",
    givenname: "User",
    description: "",
    editable: true,
    mobile: "",
    phone: "",
    userid: "123"
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditUserDialogComponent],
      providers: [
        provideHttpClient(),
        { provide: UserService, useClass: MockUserService },
        { provide: MAT_DIALOG_DATA, useValue: testUserData },
        { provide: MatDialogRef, useClass: MockMatDialogRef }
      ]
    }).compileComponents();

    mockUserService = TestBed.inject(UserService) as unknown as MockUserService;
    dialogRefMock = TestBed.inject(MatDialogRef) as unknown as MockMatDialogRef<any, any>;

    fixture = TestBed.createComponent(EditUserDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should include username in title if available", () => {
    expect(component.title()).toBe("Edit User: edituser");
  });

  it("should initialize editedUserData with input data", () => {
    expect(component.editedUserData()).toEqual(testUserData);
  });

  it("should update editedUserData on onUpdateUserData", () => {
    const newData = { ...testUserData, email: "newemail@example.com" };
    component.onUpdateUserData(newData);
    expect(component.editedUserData()).toEqual(newData);
  });

  it("should call userService.editUser on save", () => {
    mockUserService.editUser.mockReturnValue({
      subscribe: ({ next }: any) => next(true)
    });
    component.save();
    expect(mockUserService.editUser).toHaveBeenCalledWith(
      "editresolver",
      expect.objectContaining({ username: "edituser" })
    );
  });

  it("should call save always with input username", () => {
    mockUserService.editUser.mockReturnValue({
      subscribe: ({ next }: any) => next(true)
    });
    component.editedUserData.set({ ...component.editedUserData(), username: "" });
    component.save();
    expect(mockUserService.editUser).toHaveBeenCalledWith(
      "editresolver",
      expect.objectContaining({ username: "edituser" })
    );
  });

  it("should reload userResource and close dialog on successful edit", () => {
    mockUserService.editUser.mockReturnValue({
      subscribe: ({ next }: any) => next(true)
    });
    component.save();
    expect(mockUserService.userResource.reload).toHaveBeenCalled();
    expect(component.dialogRef.close).toHaveBeenCalled();
  });

  it("should keep dialog open on failed edit", () => {
    mockUserService.editUser.mockReturnValue({
      subscribe: ({ next }: any) => next(false)
    });
    dialogRefMock.close.mockClear();

    component.save();
    expect(mockUserService.userResource.reload).not.toHaveBeenCalled();
    expect(component.dialogRef.close).not.toHaveBeenCalled();
  });
});
