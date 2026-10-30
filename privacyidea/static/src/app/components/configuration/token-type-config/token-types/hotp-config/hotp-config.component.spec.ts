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
import { HOTP_HASHLIB } from "@constants/token.constants";
import { createTokenTypeConfigForm } from "@testing/token-type-config-form";
import { HotpConfigComponent } from "./hotp-config.component";

const mockHashLibs = ["sha1", "sha256", "sha512"];

describe("HotpConfigComponent", () => {
  let fixture: ComponentFixture<HotpConfigComponent>;
  let component: HotpConfigComponent;
  let configForm: ReturnType<typeof createTokenTypeConfigForm>;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const select = () => fixture.debugElement.query(By.directive(MatSelect)).componentInstance as MatSelect;

  const create = async (config: Record<string, string> = {}) => {
    configForm = createTokenTypeConfigForm(config);
    fixture = TestBed.createComponent(HotpConfigComponent);
    fixture.componentRef.setInput("config", configForm.form);
    fixture.componentRef.setInput("hashLibs", mockHashLibs);
    component = fixture.componentInstance;
    await flush();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HotpConfigComponent],
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

  it("writes the raw hashlib key to the form when a labelled option is picked", async () => {
    await create();
    select().open();
    await flush();

    const options = fixture.debugElement.queryAll(By.css("mat-option"));
    expect(options.map((option) => [option.componentInstance.value, option.nativeElement.textContent.trim()])).toEqual([
      ["sha1", "SHA-1"],
      ["sha256", "SHA-256"],
      ["sha512", "SHA-512"]
    ]);

    options[1].nativeElement.click();
    await flush();

    expect(configForm.model().values[HOTP_HASHLIB]).toBe("sha256");
    expect(configForm.form.values[HOTP_HASHLIB]().dirty()).toBe(true);
  });

  it("shows the hashlib of the form", async () => {
    await create({ [HOTP_HASHLIB]: "sha512" });
    expect(select().value).toBe("sha512");
  });

  it("shows a hashlib that is set after the panel was created", async () => {
    await create();
    configForm.model.update((model) => ({ ...model, values: { ...model.values, [HOTP_HASHLIB]: "sha256" } }));
    await flush();
    expect(select().value).toBe("sha256");
  });

  it("clears the hashlib through the form and marks the field dirty", async () => {
    await create({ [HOTP_HASHLIB]: "sha256" });
    const clearButton = fixture.debugElement.query(By.css("app-clear-button button"));

    clearButton.nativeElement.click();
    await flush();

    expect(configForm.model().values[HOTP_HASHLIB]).toBe("");
    expect(configForm.form.values[HOTP_HASHLIB]().dirty()).toBe(true);
  });
});
