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
import { WebauthnConfigComponent } from "@components/configuration/token-type-config/token-types/webauthn-config/webauthn-config.component";
import { WEBAUTHN_TRUST_ANCHOR_DIR } from "@constants/token.constants";
import { createTokenTypeConfigForm } from "@testing/token-type-config-form";

describe("WebauthnConfigComponent", () => {
  let fixture: ComponentFixture<WebauthnConfigComponent>;
  let component: WebauthnConfigComponent;
  let configForm: ReturnType<typeof createTokenTypeConfigForm>;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const input = () => fixture.nativeElement.querySelector("input") as HTMLInputElement;
  const warnings = () =>
    Array.from(fixture.nativeElement.querySelectorAll(".alert-warning") as NodeListOf<HTMLElement>).map((warning) =>
      warning.textContent?.trim()
    );

  const create = async (config: Record<string, string> = {}) => {
    configForm = createTokenTypeConfigForm(config);
    fixture = TestBed.createComponent(WebauthnConfigComponent);
    fixture.componentRef.setInput("config", configForm.form);
    component = fixture.componentInstance;
    await flush();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WebauthnConfigComponent],
      providers: [provideRouter([])]
    }).compileComponents();
  });

  it("should create", async () => {
    await create();
    expect(component).toBeTruthy();
  });

  it("shows the trust_anchor_dir of the form", async () => {
    await create({ [WEBAUTHN_TRUST_ANCHOR_DIR]: "/etc/privacyidea/test_path" });

    expect(input().value).toBe("/etc/privacyidea/test_path");
    expect(component.trustAnchorDir()).toBe("/etc/privacyidea/test_path");
  });

  it("writes the typed trust_anchor_dir to the form", async () => {
    await create();

    input().value = "/etc/privacyidea/trusted_attestation_roots";
    input().dispatchEvent(new Event("input"));
    await flush();

    expect(configForm.model().values[WEBAUTHN_TRUST_ANCHOR_DIR]).toBe("/etc/privacyidea/trusted_attestation_roots");
    expect(component.trustAnchorDir()).toBe("/etc/privacyidea/trusted_attestation_roots");
  });

  it("renders an empty input and no warning when the key is missing", async () => {
    await create();
    expect(input().value).toBe("");
    expect(warnings()).toEqual([]);
  });

  it("warns about a relative path and about a trailing slash", async () => {
    await create({ [WEBAUTHN_TRUST_ANCHOR_DIR]: "relative/path/" });

    expect(warnings()).toEqual([
      "The trust_anchor_dir must be an absolute path.",
      'The trust_anchor_dir must not end with a "/".'
    ]);
  });

  it("keeps the form valid while a warning shows", async () => {
    await create({ [WEBAUTHN_TRUST_ANCHOR_DIR]: "relative/path/" });
    expect(configForm.form().valid()).toBe(true);
  });
});
