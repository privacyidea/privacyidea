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
import { YubicoConfigComponent } from "@components/configuration/token-type-config/token-types/yubico-config/yubico-config.component";
import { YUBICO_ID, YUBICO_SECRET, YUBICO_URL } from "@constants/token.constants";
import { createTokenTypeConfigForm } from "@testing/token-type-config-form";
import { touchAll } from "@utils/form-state.utils";

describe("YubicoConfigComponent", () => {
  let fixture: ComponentFixture<YubicoConfigComponent>;
  let component: YubicoConfigComponent;
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
  const errors = () =>
    Array.from(fixture.nativeElement.querySelectorAll("mat-error") as NodeListOf<HTMLElement>).map((error) =>
      error.textContent?.trim()
    );

  const create = async (config: Record<string, string> = {}) => {
    configForm = createTokenTypeConfigForm(config);
    fixture = TestBed.createComponent(YubicoConfigComponent);
    fixture.componentRef.setInput("config", configForm.form);
    component = fixture.componentInstance;
    await flush();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [YubicoConfigComponent],
      providers: [provideRouter([])]
    }).compileComponents();
  });

  it("should create", async () => {
    await create();
    expect(component).toBeTruthy();
  });

  it("should display the values of the form", async () => {
    await create({
      [YUBICO_ID]: "12345",
      [YUBICO_SECRET]: "apiKeySecret",
      [YUBICO_URL]: "https://api.yubico.com/wsapi/2.0/verify"
    });

    expect(input("The client ID").value).toBe("12345");
    expect(input("API Key").value).toBe("apiKeySecret");
    expect(input("https://api.yubico.com/wsapi/2.0/verify").value).toBe("https://api.yubico.com/wsapi/2.0/verify");
  });

  it("writes the typed values to the form and keeps the other entries", async () => {
    await create({ [YUBICO_SECRET]: "oldSecret" });

    await type("The client ID", "newId");
    await type("https://api.yubico.com/wsapi/2.0/verify", "https://yubico.example/verify");

    expect(configForm.model().values[YUBICO_ID]).toBe("newId");
    expect(configForm.model().values[YUBICO_URL]).toBe("https://yubico.example/verify");
    expect(configForm.model().values[YUBICO_SECRET]).toBe("oldSecret");
    expect(configForm.form.values[YUBICO_ID]().dirty()).toBe(true);
  });

  describe("required entries", () => {
    it("shows no error while the panel is empty", async () => {
      await create();
      await touchAll(configForm.form);
      await flush();

      expect(errors()).toEqual([]);
      expect(configForm.form().valid()).toBe(true);
    });

    it("shows an error for each missing credential once one is filled and the form is touched", async () => {
      await create({ [YUBICO_ID]: "12345" });
      expect(errors()).toEqual([]);

      await touchAll(configForm.form);
      await flush();

      expect(errors()).toEqual(["API Key is required."]);
      expect(configForm.form().valid()).toBe(false);
    });

    it("shows only the client ID error when only the client ID is missing", async () => {
      await create({ [YUBICO_SECRET]: "secret" });
      await touchAll(configForm.form);
      await flush();

      expect(errors()).toEqual(["API Client ID is required."]);
    });

    it("removes the error once the credentials are filled", async () => {
      await create({ [YUBICO_ID]: "12345" });
      await touchAll(configForm.form);
      await flush();

      await type("API Key", "secret");

      expect(errors()).toEqual([]);
      expect(configForm.form().valid()).toBe(true);
    });

    it("does not require the URL, the backend defaults it to YubiCloud", async () => {
      await create({ [YUBICO_ID]: "12345", [YUBICO_SECRET]: "secret" });
      await touchAll(configForm.form);
      await flush();

      expect(errors()).toEqual([]);
      expect(configForm.form().valid()).toBe(true);
      expect(fixture.nativeElement.querySelector(".panel-incomplete")).toBeNull();
    });

    it("does not require the credentials when only the URL is filled", async () => {
      await create({ [YUBICO_URL]: "https://api.yubico.com/wsapi/2.0/verify" });

      expect(configForm.form().valid()).toBe(true);
    });
  });

  describe("incomplete indicator", () => {
    const indicator = () => fixture.nativeElement.querySelector(".panel-incomplete") as HTMLElement | null;

    it("appears in the header while a credential is missing and disappears once it is filled", async () => {
      await create({ [YUBICO_ID]: "12345" });
      expect(indicator()?.textContent).toContain("Incomplete");

      await type("API Key", "secret");

      expect(indicator()).toBeNull();
    });

    it("opens the panel that is incomplete and keeps it collapsible", async () => {
      await create({ [YUBICO_ID]: "12345" });
      const panel = fixture.nativeElement.querySelector("mat-expansion-panel") as HTMLElement;
      expect(panel.classList).toContain("mat-expanded");

      (fixture.nativeElement.querySelector("mat-expansion-panel-header") as HTMLElement).click();
      await type("API Key", "secret");

      expect(panel.classList).not.toContain("mat-expanded");
    });
  });

  it("should handle expanded input", async () => {
    await create();
    fixture.componentRef.setInput("expanded", true);
    fixture.detectChanges();
    expect(component.expanded()).toBe(true);

    fixture.componentRef.setInput("expanded", false);
    fixture.detectChanges();
    expect(component.expanded()).toBe(false);
  });
});
