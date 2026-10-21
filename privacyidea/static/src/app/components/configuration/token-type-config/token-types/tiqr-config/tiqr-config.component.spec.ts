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
import { provideRouter } from "@angular/router";
import { TiqrConfigComponent } from "@components/configuration/token-type-config/token-types/tiqr-config/tiqr-config.component";
import {
  TIQR_AUTH_SERVER,
  TIQR_INFO_URL,
  TIQR_LOGO_URL,
  TIQR_OCRASUITE,
  TIQR_REG_SERVER,
  TIQR_SERVICE_DISPLAYNAME,
  TIQR_SERVICE_IDENTIFIER
} from "@constants/token.constants";
import { createTokenTypeConfigForm } from "@testing/token-type-config-form";
import { touchAll } from "@utils/form-state.utils";

const REG_SERVER_PLACEHOLDER = "http://pi.server/ttype/tiqr";
const LOGO_URL_PLACEHOLDER = "https://pi.server/static/css/privacyIDEA1.png";
const INFO_URL_PLACEHOLDER = "https://www.privacyidea.org";

describe("TiqrConfigComponent", () => {
  let fixture: ComponentFixture<TiqrConfigComponent>;
  let component: TiqrConfigComponent;
  let configForm: ReturnType<typeof createTokenTypeConfigForm>;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const inputs = () => Array.from(fixture.nativeElement.querySelectorAll("input") as NodeListOf<HTMLInputElement>);
  const input = (placeholder: string) =>
    fixture.nativeElement.querySelector(`input[placeholder="${placeholder}"]`) as HTMLInputElement;
  const type = async (element: HTMLInputElement, value: string) => {
    element.value = value;
    element.dispatchEvent(new Event("input"));
    await flush();
  };
  const errors = () =>
    Array.from(fixture.nativeElement.querySelectorAll("mat-error") as NodeListOf<HTMLElement>).map((error) =>
      error.textContent?.trim()
    );

  const create = async (config: Record<string, string> = {}) => {
    configForm = createTokenTypeConfigForm(config);
    fixture = TestBed.createComponent(TiqrConfigComponent);
    fixture.componentRef.setInput("config", configForm.form);
    component = fixture.componentInstance;
    await flush();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TiqrConfigComponent],
      providers: [provideRouter([])]
    }).compileComponents();
  });

  it("should create", async () => {
    await create();
    expect(component).toBeTruthy();
  });

  it("should display the values of the form in the seven inputs", async () => {
    await create({
      [TIQR_REG_SERVER]: "http://pi.server/ttype/tiqr",
      [TIQR_AUTH_SERVER]: "http://auth.server/tiqr",
      [TIQR_SERVICE_DISPLAYNAME]: "Test Service",
      [TIQR_SERVICE_IDENTIFIER]: "org.privacyidea",
      [TIQR_LOGO_URL]: "https://pi.server/logo.png",
      [TIQR_INFO_URL]: "https://www.privacyidea.org",
      [TIQR_OCRASUITE]: "OCRA-1:HOTP-SHA1-6:QN10"
    });

    expect(inputs().map((element) => element.value)).toEqual([
      "http://pi.server/ttype/tiqr",
      "http://auth.server/tiqr",
      "Test Service",
      "org.privacyidea",
      "https://pi.server/logo.png",
      "OCRA-1:HOTP-SHA1-6:QN10",
      "https://www.privacyidea.org"
    ]);
  });

  it("writes what is typed into each input to its entry of the form", async () => {
    await create();
    const keys = [
      TIQR_REG_SERVER,
      TIQR_AUTH_SERVER,
      TIQR_SERVICE_DISPLAYNAME,
      TIQR_SERVICE_IDENTIFIER,
      TIQR_LOGO_URL,
      TIQR_OCRASUITE,
      TIQR_INFO_URL
    ];

    for (const [index, element] of inputs().entries()) {
      await type(element, `value ${index}`);
    }

    expect(keys.map((key) => configForm.model().values[key])).toEqual(keys.map((_, index) => `value ${index}`));
    expect(configForm.form.values[TIQR_OCRASUITE]().dirty()).toBe(true);
  });

  describe("required entries", () => {
    it("shows no error while the panel is empty", async () => {
      await create();
      await touchAll(configForm.form);
      await flush();

      expect(errors()).toEqual([]);
      expect(configForm.form().valid()).toBe(true);
    });

    it("shows no error before the form is touched", async () => {
      await create({ [TIQR_OCRASUITE]: "suite" });
      expect(errors()).toEqual([]);
      expect(configForm.form().valid()).toBe(false);
    });

    it("shows an error for the registration server and logo URL once another entry is filled", async () => {
      await create({ [TIQR_OCRASUITE]: "suite" });

      await touchAll(configForm.form);
      await flush();

      expect(errors()).toEqual(["TiQR Registration Server is required", "TiQR Logo URL is required"]);
    });

    it("removes each error once its entry is filled", async () => {
      await create({ [TIQR_OCRASUITE]: "suite" });
      await touchAll(configForm.form);
      await flush();

      await type(input(REG_SERVER_PLACEHOLDER), "http://pi.server/ttype/tiqr");
      expect(errors()).toEqual(["TiQR Logo URL is required"]);
      await type(input(LOGO_URL_PLACEHOLDER), "https://pi.server/logo.png");

      expect(errors()).toEqual([]);
      expect(configForm.form().valid()).toBe(true);
    });

    it("does not require the info URL, the backend defaults it", async () => {
      await create({ [TIQR_REG_SERVER]: "http://pi.server/ttype/tiqr", [TIQR_LOGO_URL]: "https://pi.server/logo.png" });
      await touchAll(configForm.form);
      await flush();

      expect(input(INFO_URL_PLACEHOLDER).value).toBe("");
      expect(errors()).toEqual([]);
      expect(configForm.form().valid()).toBe(true);
    });
  });

  describe("incomplete indicator", () => {
    const indicator = () => fixture.nativeElement.querySelector(".panel-incomplete") as HTMLElement | null;

    it("appears in the header while a required entry is missing and disappears once it is filled", async () => {
      await create({ [TIQR_OCRASUITE]: "suite" });
      expect(indicator()?.textContent).toContain("Incomplete");

      await type(input(REG_SERVER_PLACEHOLDER), "http://pi.server/ttype/tiqr");
      expect(indicator()).not.toBeNull();
      await type(input(LOGO_URL_PLACEHOLDER), "https://pi.server/logo.png");

      expect(indicator()).toBeNull();
    });

    it("is not shown for an empty panel", async () => {
      await create();

      expect(indicator()).toBeNull();
    });
  });
});
