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
import { BlocklistBlockDialogComponent, BlocklistBlockDialogResult } from "./blocklist-block-dialog.component";

describe("BlocklistBlockDialogComponent", () => {
  let component: BlocklistBlockDialogComponent;
  let fixture: ComponentFixture<BlocklistBlockDialogComponent>;
  let el: HTMLElement;

  const dialogRefMock = {
    close: jest.fn()
  } as unknown as jest.Mocked<MatDialogRef<BlocklistBlockDialogComponent, BlocklistBlockDialogResult | null>>;

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
    component.blockForm
      .durationInput()
      .errors()
      .map((e) => e.kind);
  const typeIp = async (value: string) => {
    const input = el.querySelector("input:not([type=number]):not([type=radio])") as HTMLInputElement;
    input.value = value;
    input.dispatchEvent(new Event("input"));
    await flush();
  };

  beforeEach(async () => {
    jest.clearAllMocks();
    await TestBed.configureTestingModule({
      imports: [BlocklistBlockDialogComponent],
      providers: [
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: undefined }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(BlocklistBlockDialogComponent);
    component = fixture.componentInstance;
    el = fixture.nativeElement;
    await flush();
  });

  it("cannot be confirmed without an address", async () => {
    expect(component.blockForm().valid()).toBe(false);
    expect(
      component.blockForm
        .ip()
        .errors()
        .map((e) => e.kind)
    ).toEqual([ERR.required]);

    await typeIp("  ");

    expect(component.blockForm().valid()).toBe(false);
    expect(
      component.blockForm
        .ip()
        .errors()
        .map((e) => e.kind)
    ).toEqual([ERR.required]);

    await typeIp("203.0.113.9");

    expect(component.blockForm().valid()).toBe(true);
  });

  it("renders the missing address message once the address is touched", async () => {
    expect(errorTexts()).toEqual([]);

    el.querySelector("input")?.dispatchEvent(new Event("blur"));
    await flush();

    expect(errorTexts()).toEqual(["IP address is required"]);
  });

  it("disables the confirm action while the address is missing", async () => {
    expect(component.dialogActions()[0].disabled).toBe(true);

    await typeIp("203.0.113.9");

    expect(component.dialogActions()[0].disabled).toBe(false);
  });

  it("closes with a trimmed address and a null duration for a permanent block", async () => {
    await typeIp(" 203.0.113.9 ");

    component.onAction("confirm");

    expect(dialogRefMock.close).toHaveBeenCalledWith({ ip: "203.0.113.9", durationSeconds: null });
  });

  it("does not close without an address", () => {
    component.onAction("confirm");

    expect(dialogRefMock.close).not.toHaveBeenCalled();
  });

  // The timed controls stay in the layout while permanent is selected (so switching modes does not shift
  // the dialog) and are only disabled; picking "timed" enables them again.
  it("disables the timed controls while permanent, enabling them for a timed block", async () => {
    const unit = el.querySelector("mat-select") as HTMLElement;
    expect(durationInput().disabled).toBe(true);
    expect(unit.getAttribute("aria-disabled")).toBe("true");
    expect(component.blockForm.durationInput().disabled()).toBe(true);
    expect(component.blockForm.durationUnit().disabled()).toBe(true);

    await selectTimed();

    expect(component.blockModel().mode).toBe("timed");
    expect(durationInput().disabled).toBe(false);
    expect(unit.getAttribute("aria-disabled")).toBe("false");
  });

  it("shows the selected unit in the select", () => {
    const select = fixture.debugElement.query(By.directive(MatSelect)).componentInstance as MatSelect;

    expect(select.value).toBe("minutes");
  });

  it("is valid in permanent mode even though the disabled duration is empty", async () => {
    await typeIp("203.0.113.9");

    expect(component.blockModel().durationInput).toBeNull();
    expect(component.blockForm.durationInput().errors()).toEqual([]);
    expect(component.blockForm().valid()).toBe(true);
  });

  // A timed block has to carry a duration the backend would accept, so the action stays disabled until it does.
  it("cannot be confirmed until a timed block has a valid duration", async () => {
    await typeIp("203.0.113.9");
    await selectTimed();
    expect(component.blockForm().valid()).toBe(false);
    expect(durationKinds()).toEqual([ERR.required]);

    await typeDuration("0");
    expect(durationKinds()).toEqual([POSITIVE_INTEGER_ERROR]);
    expect(component.blockForm().valid()).toBe(false);

    await typeDuration("-3");
    expect(durationKinds()).toEqual([POSITIVE_INTEGER_ERROR]);

    await typeDuration("1.5");
    expect(durationKinds()).toEqual([POSITIVE_INTEGER_ERROR]);

    await typeDuration("5");
    expect(durationKinds()).toEqual([]);
    expect(component.blockForm().valid()).toBe(true);
    expect(component.dialogActions()[0].disabled).toBe(false);
  });

  it("writes the typed duration as a number to the model and marks it dirty", async () => {
    await selectTimed();
    expect(component.blockForm.durationInput().dirty()).toBe(false);

    await typeDuration("7");

    expect(component.blockModel().durationInput).toBe(7);
    expect(component.blockForm.durationInput().dirty()).toBe(true);
  });

  it("keeps the confirm action disabled for a timed block without a duration", async () => {
    await typeIp("203.0.113.9");
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
    await typeIp("203.0.113.9");
    await selectTimed();
    stubBadInput(true);
    await typeDuration("");

    expect(durationKinds()).toContain(ERR.parse);
    expect(component.blockForm().valid()).toBe(false);

    durationInput().dispatchEvent(new Event("blur"));
    await flush();
    expect(errorTexts()).toEqual(["Duration must be a number"]);
  });

  it("does not close while a timed block has no valid duration", async () => {
    await typeIp("203.0.113.9");
    await selectTimed();

    component.onAction("confirm");

    expect(dialogRefMock.close).not.toHaveBeenCalled();
  });

  it("converts the entered duration to seconds using the selected unit", async () => {
    await typeIp("203.0.113.9");
    await selectTimed();
    await typeDuration("2");
    component.blockModel.update((m) => ({ ...m, durationUnit: "hours" }));
    await flush();

    component.onAction("confirm");

    expect(dialogRefMock.close).toHaveBeenCalledWith({ ip: "203.0.113.9", durationSeconds: 7200 });
  });

  it("takes the unit chosen in the select", async () => {
    await typeIp("203.0.113.9");
    await selectTimed();
    await typeDuration("3");
    const select = fixture.debugElement.query(By.directive(MatSelect)).componentInstance as MatSelect;
    select.open();
    await flush();
    (document.querySelectorAll("mat-option")[2] as HTMLElement).click();
    await flush();

    expect(component.blockModel().durationUnit).toBe("hours");
    component.onAction("confirm");
    expect(dialogRefMock.close).toHaveBeenCalledWith({ ip: "203.0.113.9", durationSeconds: 10800 });
  });

  it("ignores a leftover duration once permanent is selected again", async () => {
    await typeIp("203.0.113.9");
    await selectTimed();
    await typeDuration("5");
    radios()[0].click();
    await flush();

    expect(component.blockForm().valid()).toBe(true);
    component.onAction("confirm");

    expect(dialogRefMock.close).toHaveBeenCalledWith({ ip: "203.0.113.9", durationSeconds: null });
  });

  it("ignores an action other than confirm", () => {
    component.onAction("cancel");

    expect(dialogRefMock.close).not.toHaveBeenCalled();
  });
});
