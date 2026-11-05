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
import { DAYPASSWORD_HASHLIB, DAYPASSWORD_TIME_STEP } from "@constants/token.constants";
import { createTokenTypeConfigForm } from "@testing/token-type-config-form";
import { touchAll } from "@utils/form-state.utils";
import { DaypasswordConfigComponent } from "./daypassword-config.component";

const mockHashLibs = ["sha1", "sha256", "sha512"];

describe("DaypasswordConfigComponent", () => {
  let fixture: ComponentFixture<DaypasswordConfigComponent>;
  let component: DaypasswordConfigComponent;
  let configForm: ReturnType<typeof createTokenTypeConfigForm>;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const timeStepInput = () => fixture.nativeElement.querySelector("input") as HTMLInputElement;
  const errors = () =>
    Array.from(fixture.nativeElement.querySelectorAll("mat-error") as NodeListOf<HTMLElement>).map((error) =>
      error.textContent?.trim()
    );

  const create = async (config: Record<string, string> = {}) => {
    configForm = createTokenTypeConfigForm(config);
    fixture = TestBed.createComponent(DaypasswordConfigComponent);
    fixture.componentRef.setInput("config", configForm.form);
    fixture.componentRef.setInput("hashLibs", mockHashLibs);
    component = fixture.componentInstance;
    await flush();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DaypasswordConfigComponent]
    }).compileComponents();
  });

  afterEach(() => {
    document.querySelectorAll(".cdk-overlay-container").forEach((container) => (container.innerHTML = ""));
  });

  it("should create", async () => {
    await create();
    expect(component).toBeTruthy();
  });

  it("shows the values of the form", async () => {
    await create({ [DAYPASSWORD_TIME_STEP]: "24h", [DAYPASSWORD_HASHLIB]: "sha256" });

    expect(timeStepInput().value).toBe("24h");
    expect((fixture.debugElement.query(By.directive(MatSelect)).componentInstance as MatSelect).value).toBe("sha256");
  });

  it("writes the typed time step to the form", async () => {
    await create();

    timeStepInput().value = "12h";
    timeStepInput().dispatchEvent(new Event("input"));
    await flush();

    expect(configForm.model().values[DAYPASSWORD_TIME_STEP]).toBe("12h");
    expect(configForm.form.values[DAYPASSWORD_TIME_STEP]().dirty()).toBe(true);
  });

  it("writes the picked hashlib to the form", async () => {
    await create();
    const select = fixture.debugElement.query(By.directive(MatSelect)).componentInstance as MatSelect;
    select.open();
    await flush();

    (document.querySelectorAll("mat-option")[1] as HTMLElement).click();
    await flush();

    expect(configForm.model().values[DAYPASSWORD_HASHLIB]).toBe("sha256");
  });

  it("clears the hashlib through the form and marks the field dirty", async () => {
    await create({ [DAYPASSWORD_TIME_STEP]: "24h", [DAYPASSWORD_HASHLIB]: "sha256" });

    fixture.debugElement.query(By.css("app-clear-button button")).nativeElement.click();
    await flush();

    expect(configForm.model().values[DAYPASSWORD_HASHLIB]).toBe("");
    expect(configForm.form.values[DAYPASSWORD_HASHLIB]().dirty()).toBe(true);
  });

  describe("default entries", () => {
    it("is valid and shows no error with only the hashlib chosen", async () => {
      await create({ [DAYPASSWORD_HASHLIB]: "sha1" });

      await touchAll(configForm.form);
      await flush();

      expect(errors()).toEqual([]);
      expect(configForm.form().valid()).toBe(true);
    });

    it("is valid and shows no error with only the time step typed", async () => {
      await create({ [DAYPASSWORD_TIME_STEP]: "24h" });

      await touchAll(configForm.form);
      await flush();

      expect(errors()).toEqual([]);
      expect(configForm.form().valid()).toBe(true);
    });
  });
});
