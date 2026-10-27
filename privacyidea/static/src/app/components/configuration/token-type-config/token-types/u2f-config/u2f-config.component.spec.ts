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
import { U2fConfigComponent } from "@components/configuration/token-type-config/token-types/u2f-config/u2f-config.component";
import { U2F_APP_ID } from "@constants/token.constants";
import { createTokenTypeConfigForm } from "@testing/token-type-config-form";

describe("U2fConfigComponent", () => {
  let fixture: ComponentFixture<U2fConfigComponent>;
  let component: U2fConfigComponent;
  let configForm: ReturnType<typeof createTokenTypeConfigForm>;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const input = () => fixture.nativeElement.querySelector("input") as HTMLInputElement;
  const type = async (value: string) => {
    input().value = value;
    input().dispatchEvent(new Event("input"));
    await flush();
  };
  const warnings = () =>
    Array.from(fixture.nativeElement.querySelectorAll(".alert-warning") as NodeListOf<HTMLElement>).map((warning) =>
      warning.textContent?.trim()
    );

  const create = async (config: Record<string, string> = {}) => {
    configForm = createTokenTypeConfigForm(config);
    fixture = TestBed.createComponent(U2fConfigComponent);
    fixture.componentRef.setInput("config", configForm.form);
    component = fixture.componentInstance;
    await flush();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [U2fConfigComponent],
      providers: [provideRouter([])]
    }).compileComponents();
  });

  it("should create", async () => {
    await create();
    expect(component).toBeTruthy();
  });

  it("renders an empty input and no warning when the key is missing", async () => {
    await create();
    expect(input().value).toBe("");
    expect(warnings()).toEqual([]);
  });

  it("shows the configured appId in the input", async () => {
    await create({ [U2F_APP_ID]: "https://pi.server.com" });

    expect(input().value).toBe("https://pi.server.com");
    expect(warnings()).toEqual([]);
  });

  it("writes the typed appId to the form", async () => {
    await create();

    await type("https://pi.server.com");

    expect(configForm.model().values[U2F_APP_ID]).toBe("https://pi.server.com");
    expect(configForm.form.values[U2F_APP_ID]().dirty()).toBe(true);
    expect(component.appId()).toBe("https://pi.server.com");
  });

  it("warns about a non-https appId and about a trailing slash", async () => {
    await create({ [U2F_APP_ID]: "http://pi.server.com/" });

    expect(warnings()).toEqual(['The AppID needs to start with "https".', 'The AppID must not end with a "/".']);
  });

  it("updates the warnings while the appId is typed and keeps the form valid", async () => {
    await create();

    await type("http://pi.server.com");
    expect(warnings()).toEqual(['The AppID needs to start with "https".']);
    await type("https://pi.server.com/");
    expect(warnings()).toEqual(['The AppID must not end with a "/".']);
    expect(configForm.form().valid()).toBe(true);
  });
});
