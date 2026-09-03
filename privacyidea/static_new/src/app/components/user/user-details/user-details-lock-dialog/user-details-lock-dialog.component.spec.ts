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

import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { UserDetailsLockDialogComponent, UserDetailsLockDialogResult } from "./user-details-lock-dialog.component";

describe("UserDetailsLockDialogComponent", () => {
  let component: UserDetailsLockDialogComponent;
  let fixture: ComponentFixture<UserDetailsLockDialogComponent>;

  const dialogRefMock = {
    close: jest.fn()
  } as unknown as jest.Mocked<MatDialogRef<UserDetailsLockDialogComponent, UserDetailsLockDialogResult | null>>;

  beforeEach(async () => {
    jest.clearAllMocks();
    await TestBed.configureTestingModule({
      imports: [UserDetailsLockDialogComponent],
      providers: [
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: { username: "alice", realm: "realm1" } }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(UserDetailsLockDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create and default to a permanent lock", () => {
    expect(component).toBeTruthy();
    expect(component.mode()).toBe("permanent");
    expect(component.canConfirm()).toBe(true);
  });

  it("closes with a null duration for a permanent lock", () => {
    component.onAction("confirm");
    expect(dialogRefMock.close).toHaveBeenCalledWith({ durationSeconds: null });
  });

  // A timed lock has to carry a duration the backend would accept, so the action stays disabled until it does.
  it("cannot be confirmed until a timed lock has a valid duration", () => {
    component.mode.set("timed");
    expect(component.canConfirm()).toBe(false);
    component.durationInput.set("0");
    expect(component.canConfirm()).toBe(false);
    component.durationInput.set("abc");
    expect(component.canConfirm()).toBe(false);
    component.durationInput.set("5");
    expect(component.canConfirm()).toBe(true);
  });

  it("does not close while the duration is missing", () => {
    component.mode.set("timed");
    component.onAction("confirm");
    expect(dialogRefMock.close).not.toHaveBeenCalled();
  });

  it("converts the entered duration to seconds using the selected unit", () => {
    component.mode.set("timed");
    component.durationInput.set("2");
    component.durationUnit.set("minutes");
    component.onAction("confirm");
    expect(dialogRefMock.close).toHaveBeenCalledWith({ durationSeconds: 120 });
  });

  it("ignores an action other than confirm", () => {
    component.onAction("cancel");
    expect(dialogRefMock.close).not.toHaveBeenCalled();
  });

  // The timed controls stay in the layout while permanent is selected (so switching modes does not shift
  // the dialog) and are only disabled; picking "timed" enables them again.
  it("disables the timed controls while permanent, enabling them for a timed lock", () => {
    expect(component.durationDisabled()).toBe(true);
    component.mode.set("timed");
    expect(component.durationDisabled()).toBe(false);
  });
});
