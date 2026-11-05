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
import { MatSelect } from "@angular/material/select";
import { By } from "@angular/platform-browser";
import { provideRouter } from "@angular/router";
import { TotpConfigComponent } from "@components/configuration/token-type-config/token-types/totp-config/totp-config.component";
import { TOTP_HASHLIB, TOTP_TIME_SHIFT, TOTP_TIME_STEP, TOTP_TIME_WINDOW } from "@constants/token.constants";
import { createTokenTypeConfigForm } from "@testing/token-type-config-form";

const mockTotpSteps = ["30", "60"];
const mockHashLibs = ["sha1", "sha256", "sha512"];

describe("TotpConfigComponent", () => {
  let fixture: ComponentFixture<TotpConfigComponent>;
  let component: TotpConfigComponent;
  let configForm: ReturnType<typeof createTokenTypeConfigForm>;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const input = (placeholder: string) =>
    fixture.nativeElement.querySelector(`input[placeholder="${placeholder}"]`) as HTMLInputElement;
  const type = async (placeholder: string, value: string) => {
    input(placeholder).value = value;
    input(placeholder).dispatchEvent(new Event("input"));
    await flush();
  };
  const selects = () =>
    fixture.debugElement.queryAll(By.directive(MatSelect)).map((s) => s.componentInstance as MatSelect);
  const pick = async (select: MatSelect, index: number) => {
    document.querySelectorAll(".cdk-overlay-container").forEach((container) => (container.innerHTML = ""));
    select.open();
    await flush();
    (document.querySelectorAll("mat-option")[index] as HTMLElement).click();
    await flush();
  };

  const create = async (config: Record<string, string> = {}) => {
    configForm = createTokenTypeConfigForm(config);
    fixture = TestBed.createComponent(TotpConfigComponent);
    fixture.componentRef.setInput("config", configForm.form);
    fixture.componentRef.setInput("totpSteps", mockTotpSteps);
    fixture.componentRef.setInput("hashLibs", mockHashLibs);
    component = fixture.componentInstance;
    await flush();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TotpConfigComponent],
      providers: [provideRouter([])]
    }).compileComponents();
  });

  afterEach(() => {
    document.querySelectorAll(".cdk-overlay-container").forEach((container) => (container.innerHTML = ""));
  });

  it("should create", async () => {
    await create();
    expect(component).toBeTruthy();
  });

  it("should display the values of the form", async () => {
    await create({
      [TOTP_TIME_STEP]: "60",
      [TOTP_TIME_WINDOW]: "240",
      [TOTP_TIME_SHIFT]: "-5",
      [TOTP_HASHLIB]: "sha256"
    });

    const [stepSelect, hashlibSelect] = selects();
    expect(stepSelect.value).toBe("60");
    expect(hashlibSelect.value).toBe("sha256");
    expect(input("180").value).toBe("240");
    expect(input("0").value).toBe("-5");
  });

  it("writes the picked time step and hashlib to the form", async () => {
    await create();
    const [stepSelect, hashlibSelect] = selects();

    await pick(stepSelect, 1);
    expect(configForm.model().values[TOTP_TIME_STEP]).toBe("60");
    await pick(hashlibSelect, 2);
    expect(configForm.model().values[TOTP_HASHLIB]).toBe("sha512");
  });

  it("writes the typed time window and a negative time shift as strings", async () => {
    await create();

    await type("180", "240");
    await type("0", "-10");

    expect(configForm.model().values[TOTP_TIME_WINDOW]).toBe("240");
    expect(configForm.model().values[TOTP_TIME_SHIFT]).toBe("-10");
    expect(configForm.form().valid()).toBe(true);
  });

  it("writes an empty string, not NaN, when a number input is cleared", async () => {
    await create({ [TOTP_TIME_WINDOW]: "180", [TOTP_TIME_SHIFT]: "5" });

    await type("180", "");
    await type("0", "");

    expect(configForm.model().values[TOTP_TIME_WINDOW]).toBe("");
    expect(configForm.model().values[TOTP_TIME_SHIFT]).toBe("");
  });

  it("shows a message for text the number input cannot parse", async () => {
    await create({ [TOTP_TIME_WINDOW]: "180" });
    Object.defineProperty(input("180"), "validity", { value: { badInput: true } });

    await type("180", "");
    configForm.form.values[TOTP_TIME_WINDOW]().markAsTouched();
    await flush();

    expect(
      configForm.form.values[TOTP_TIME_WINDOW]()
        .errors()
        .map((error) => error.kind)
    ).toEqual(["parse"]);
    expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain("Enter a valid number.");
    expect(configForm.form().valid()).toBe(false);
    expect(fixture.nativeElement.querySelector(".panel-incomplete")?.textContent).toContain("Incomplete");
  });

  it("shows the parse message for the time shift", async () => {
    await create();
    Object.defineProperty(input("0"), "validity", { value: { badInput: true } });

    await type("0", "");
    configForm.form.values[TOTP_TIME_SHIFT]().markAsTouched();
    await flush();

    expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain("Enter a valid number.");
  });

  it("clears the time step and the hashlib through the form and marks them dirty", async () => {
    await create({ [TOTP_TIME_STEP]: "30", [TOTP_HASHLIB]: "sha1" });
    const clearButtons = fixture.debugElement.queryAll(By.css("app-clear-button button"));

    clearButtons[0].nativeElement.click();
    clearButtons[1].nativeElement.click();
    await flush();

    expect(configForm.model().values[TOTP_TIME_STEP]).toBe("");
    expect(configForm.model().values[TOTP_HASHLIB]).toBe("");
    expect(configForm.form.values[TOTP_TIME_STEP]().dirty()).toBe(true);
    expect(configForm.form.values[TOTP_HASHLIB]().dirty()).toBe(true);
  });
});
