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
import { By } from "@angular/platform-browser";
import { ERR } from "@utils/form-rules.utils";
import { UserDetailsPinDialogComponent } from "./user-details-pin-dialog.component";

describe("UserDetailsPinDialogComponent", () => {
  let component: UserDetailsPinDialogComponent;
  let fixture: ComponentFixture<UserDetailsPinDialogComponent>;
  let el: HTMLElement;

  const dialogRefMock = {
    close: jest.fn()
  } as unknown as jest.Mocked<MatDialogRef<UserDetailsPinDialogComponent, string | null>>;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const inputs = () => Array.from(el.querySelectorAll("input")) as HTMLInputElement[];
  const type = async (input: HTMLInputElement, value: string) => {
    input.value = value;
    input.dispatchEvent(new Event("input"));
    await flush();
  };
  const confirmButton = () =>
    fixture.debugElement.query(By.css(".pi-dialog-footer .action-button-primary"))?.nativeElement as HTMLButtonElement;
  const kinds = () =>
    component.pinForm
      .pinRepeat()
      .errors()
      .map((e) => e.kind);

  beforeEach(async () => {
    jest.clearAllMocks();
    await TestBed.configureTestingModule({
      imports: [UserDetailsPinDialogComponent],
      providers: [
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: {} }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(UserDetailsPinDialogComponent);
    component = fixture.componentInstance;
    el = fixture.nativeElement;
    await flush();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("is valid with both fields empty, because the PIN is optional", () => {
    expect(component.pinForm().valid()).toBe(true);
    expect(confirmButton().disabled).toBe(false);
  });

  it("writes typed text from both inputs to the model", async () => {
    const [pin, repeat] = inputs();
    await type(pin, "1234");
    await type(repeat, "1234");
    expect(component.pinModel()).toEqual({ pin: "1234", pinRepeat: "1234" });
    expect(component.pinForm.pin().dirty()).toBe(true);
    expect(component.pinForm.pinRepeat().dirty()).toBe(true);
  });

  it('should disable "assign" when PINs do not match', async () => {
    const [pin, repeat] = inputs();
    await type(pin, "1234");
    await type(repeat, "4321");

    expect(kinds()).toEqual([ERR.pinMismatch]);
    expect(confirmButton().disabled).toBe(true);
  });

  it('should enable "assign" when PINs match', async () => {
    const [pin, repeat] = inputs();
    await type(pin, "1234");
    await type(repeat, "1234");

    expect(component.pinForm().valid()).toBe(true);
    expect(confirmButton().disabled).toBe(false);
  });

  it("re-checks the repeat when the PIN changes afterwards", async () => {
    const [pin, repeat] = inputs();
    await type(pin, "1234");
    await type(repeat, "1234");
    await type(pin, "12345");

    expect(kinds()).toEqual([ERR.pinMismatch]);
    expect(confirmButton().disabled).toBe(true);
  });

  it("shows the mismatch message once the repeat is touched, also when the repeat is empty", async () => {
    const [pin, repeat] = inputs();
    await type(pin, "1234");
    expect(el.querySelector("mat-error")).toBeNull();

    repeat.dispatchEvent(new Event("blur"));
    await flush();

    expect(component.pinForm.pinRepeat().touched()).toBe(true);
    expect(el.querySelector("mat-error")?.textContent).toContain("PINs do not match");
  });

  it("does not show the mismatch message while the PINs match", async () => {
    const [pin, repeat] = inputs();
    await type(pin, "1234");
    await type(repeat, "1234");
    repeat.dispatchEvent(new Event("blur"));
    await flush();

    expect(el.querySelector("mat-error")).toBeNull();
  });

  it("toggles the visibility of both inputs together", async () => {
    expect(inputs().map((input) => input.type)).toEqual(["password", "password"]);
    component.togglePinVisibility();
    await flush();
    expect(inputs().map((input) => input.type)).toEqual(["text", "text"]);
  });

  it("should return the PIN on confirm", async () => {
    const [pin, repeat] = inputs();
    await type(pin, "1234");
    await type(repeat, "1234");

    component.onAction("confirm");

    expect(dialogRefMock.close).toHaveBeenCalledWith("1234");
  });

  it("returns an empty PIN on confirm when none was entered", () => {
    component.onAction("confirm");

    expect(dialogRefMock.close).toHaveBeenCalledWith("");
  });

  it("does not close while the PINs differ", async () => {
    const [pin] = inputs();
    await type(pin, "1234");

    component.onAction("confirm");

    expect(dialogRefMock.close).not.toHaveBeenCalled();
  });

  it("ignores an action other than confirm", () => {
    component.onAction("cancel");

    expect(dialogRefMock.close).not.toHaveBeenCalled();
  });
});
