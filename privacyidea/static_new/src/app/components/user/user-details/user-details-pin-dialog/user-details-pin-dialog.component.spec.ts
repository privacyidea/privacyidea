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

import { UserDetailsPinDialogComponent } from "./user-details-pin-dialog.component";
import { By } from "@angular/platform-browser";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";

describe("UserDetailsPinDialogComponent", () => {
  let component: UserDetailsPinDialogComponent;
  let fixture: ComponentFixture<UserDetailsPinDialogComponent>;

  const dialogRefMock = {
    close: jest.fn()
  } as unknown as jest.Mocked<MatDialogRef<UserDetailsPinDialogComponent, string | null>>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserDetailsPinDialogComponent],
      providers: [
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: {} }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(UserDetailsPinDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it('should disable "assign" when PINs do not match', async () => {
    component.pin.set("1234");
    component.pinRepeat.set("4321");
    fixture.detectChanges();

    const assignBtn = fixture.debugElement.query(By.css(".pi-dialog-footer .action-button-1"))
      ?.nativeElement as HTMLButtonElement;

    expect(assignBtn).toBeDefined();
    expect(assignBtn.disabled).toBe(true);
  });
  it('should enable "assign" when PINs match', () => {
    component.pin.set("1234");
    component.pinRepeat.set("1234");
    fixture.detectChanges();

    const assignBtn = fixture.debugElement.query(By.css(".pi-dialog-footer .action-button-1"))
      ?.nativeElement as HTMLButtonElement;

    expect(assignBtn).toBeDefined();
    expect(assignBtn.disabled).toBe(false);
  });

  it("should return the PIN on confirm", () => {
    component.pin.set("1234");
    component.pinRepeat.set("1234");

    component.onAction("confirm");

    expect(dialogRefMock.close).toHaveBeenCalledWith("1234");
  });
});
