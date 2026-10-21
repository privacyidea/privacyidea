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
import { MatSelect } from "@angular/material/select";
import { By } from "@angular/platform-browser";
import { POSITIVE_INTEGER_ERROR } from "@utils/duration-unit.utils";
import { ERR } from "@utils/form-rules.utils";
import { UserDetailsLockDialogComponent, UserDetailsLockDialogResult } from "./user-details-lock-dialog.component";

describe("UserDetailsLockDialogComponent", () => {
  let component: UserDetailsLockDialogComponent;
  let fixture: ComponentFixture<UserDetailsLockDialogComponent>;
  let el: HTMLElement;

  const dialogRefMock = {
    close: jest.fn()
  } as unknown as jest.Mocked<MatDialogRef<UserDetailsLockDialogComponent, UserDetailsLockDialogResult | null>>;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const durationInput = () => el.querySelector("input[type=number]") as HTMLInputElement;
  const radios = () => Array.from(el.querySelectorAll("input[type=radio]")) as HTMLInputElement[];
  const typeDuration = async (value: string) => {
    durationInput().value = value;
    durationInput().dispatchEvent(new Event("input"));
    await flush();
  };
  const stubBadInput = (badInput: boolean) =>
    jest.spyOn(durationInput(), "validity", "get").mockReturnValue({ badInput } as ValidityState);
  const selectTimed = async () => {
    radios()[1].click();
    await flush();
  };
  const errorTexts = () => Array.from(el.querySelectorAll("mat-error")).map((e) => e.textContent?.trim());
  const durationKinds = () =>
    component.lockForm
      .durationInput()
      .errors()
      .map((e) => e.kind);

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
    el = fixture.nativeElement;
    await flush();
  });

  it("should create and default to a permanent lock", () => {
    expect(component).toBeTruthy();
    expect(component.lockModel().mode).toBe("permanent");
    expect(component.lockForm().valid()).toBe(true);
    expect(radios()[0].checked).toBe(true);
  });

  it("closes with a null duration for a permanent lock", () => {
    component.onAction("confirm");

    expect(dialogRefMock.close).toHaveBeenCalledWith({ durationSeconds: null });
  });

  // The timed controls stay in the layout while permanent is selected (so switching modes does not shift
  // the dialog) and are only disabled; picking "timed" enables them again.
  it("disables the timed controls while permanent, enabling them for a timed lock", async () => {
    const unit = el.querySelector("mat-select") as HTMLElement;
    expect(durationInput().disabled).toBe(true);
    expect(unit.getAttribute("aria-disabled")).toBe("true");
    expect(component.lockForm.durationInput().disabled()).toBe(true);
    expect(component.lockForm.durationUnit().disabled()).toBe(true);

    await selectTimed();

    expect(component.lockModel().mode).toBe("timed");
    expect(durationInput().disabled).toBe(false);
    expect(unit.getAttribute("aria-disabled")).toBe("false");
  });

  it("shows the selected unit in the select", () => {
    const select = fixture.debugElement.query(By.directive(MatSelect)).componentInstance as MatSelect;

    expect(select.value).toBe("minutes");
  });

  it("is valid in permanent mode even though the disabled duration is empty", () => {
    expect(component.lockModel().durationInput).toBeNull();
    expect(component.lockForm.durationInput().errors()).toEqual([]);
    expect(component.lockForm().valid()).toBe(true);
  });

  // A timed lock has to carry a duration the backend would accept, so the action stays disabled until it does.
  it("cannot be confirmed until a timed lock has a valid duration", async () => {
    await selectTimed();
    expect(component.lockForm().valid()).toBe(false);
    expect(durationKinds()).toEqual([ERR.required]);

    await typeDuration("0");
    expect(durationKinds()).toEqual([POSITIVE_INTEGER_ERROR]);
    expect(component.lockForm().valid()).toBe(false);

    await typeDuration("-3");
    expect(durationKinds()).toEqual([POSITIVE_INTEGER_ERROR]);

    await typeDuration("1.5");
    expect(durationKinds()).toEqual([POSITIVE_INTEGER_ERROR]);

    await typeDuration("5");
    expect(durationKinds()).toEqual([]);
    expect(component.lockForm().valid()).toBe(true);
    expect(component.dialogActions()[0].disabled).toBe(false);
  });

  it("writes the typed duration as a number to the model and marks it dirty", async () => {
    await selectTimed();
    expect(component.lockForm.durationInput().dirty()).toBe(false);

    await typeDuration("7");

    expect(component.lockModel().durationInput).toBe(7);
    expect(component.lockForm.durationInput().dirty()).toBe(true);
  });

  it("keeps the confirm action disabled for a timed lock without a duration", async () => {
    await selectTimed();

    expect(component.dialogActions()[0].disabled).toBe(true);
  });

  it("renders the duration messages once the field is touched", async () => {
    await selectTimed();
    expect(errorTexts()).toEqual([]);

    durationInput().dispatchEvent(new Event("blur"));
    await flush();
    expect(errorTexts()).toEqual(["Duration is required"]);

    await typeDuration("0");
    expect(errorTexts()).toEqual(["Duration must be a whole number greater than zero"]);

    await typeDuration("3");
    expect(errorTexts()).toEqual([]);
  });

  it("reports text the browser cannot read as a number as a parse error and blocks the form", async () => {
    await selectTimed();
    stubBadInput(true);
    await typeDuration("");

    expect(durationKinds()).toContain(ERR.parse);
    expect(component.lockForm().valid()).toBe(false);

    durationInput().dispatchEvent(new Event("blur"));
    await flush();
    expect(errorTexts()).toEqual(["Duration must be a number"]);
  });

  it("does not close while a timed lock has no valid duration", async () => {
    await selectTimed();

    component.onAction("confirm");

    expect(dialogRefMock.close).not.toHaveBeenCalled();
  });

  it("converts the entered duration to seconds using the selected unit", async () => {
    await selectTimed();
    await typeDuration("2");
    component.lockModel.update((m) => ({ ...m, durationUnit: "minutes" }));
    await flush();

    component.onAction("confirm");

    expect(dialogRefMock.close).toHaveBeenCalledWith({ durationSeconds: 120 });
  });

  it("takes the unit chosen in the select", async () => {
    await selectTimed();
    await typeDuration("3");
    const select = fixture.debugElement.query(By.directive(MatSelect)).componentInstance as MatSelect;
    select.open();
    await flush();
    (document.querySelectorAll("mat-option")[2] as HTMLElement).click();
    await flush();

    expect(component.lockModel().durationUnit).toBe("hours");
    component.onAction("confirm");
    expect(dialogRefMock.close).toHaveBeenCalledWith({ durationSeconds: 10800 });
  });

  it("ignores a leftover duration once permanent is selected again", async () => {
    await selectTimed();
    await typeDuration("5");
    radios()[0].click();
    await flush();

    expect(component.lockForm().valid()).toBe(true);
    component.onAction("confirm");

    expect(dialogRefMock.close).toHaveBeenCalledWith({ durationSeconds: null });
  });

  it("ignores an action other than confirm", () => {
    component.onAction("cancel");

    expect(dialogRefMock.close).not.toHaveBeenCalled();
  });
});
