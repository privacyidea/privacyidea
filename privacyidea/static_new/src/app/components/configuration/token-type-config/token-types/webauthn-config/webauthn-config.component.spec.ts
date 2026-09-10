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

describe("WebauthnConfigComponent", () => {
  let fixture: ComponentFixture<WebauthnConfigComponent>;
  let component: WebauthnConfigComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WebauthnConfigComponent],
      providers: [provideRouter([])]
    }).compileComponents();
    fixture = TestBed.createComponent(WebauthnConfigComponent);
    fixture.componentRef.setInput("formData", {});
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should emit formDataChange when updateFormData is called", () => {
    jest.spyOn(component.formDataChange, "emit");
    const newValue = "/etc/privacyidea/trusted_attestation_roots";
    component.updateFormData(WEBAUTHN_TRUST_ANCHOR_DIR, newValue);
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [WEBAUTHN_TRUST_ANCHOR_DIR]: newValue });
  });

  it("should display current formData value for trust_anchor_dir", () => {
    const testPath = "/etc/privacyidea/test_path";
    const testData = {
      [WEBAUTHN_TRUST_ANCHOR_DIR]: testPath
    };
    fixture.componentRef.setInput("formData", testData);
    fixture.detectChanges();

    expect(component.formData()[WEBAUTHN_TRUST_ANCHOR_DIR]).toEqual(testPath);
  });

  it("should handle empty trust_anchor_dir value", () => {
    jest.spyOn(component.formDataChange, "emit");
    const newValue = "";
    component.updateFormData(WEBAUTHN_TRUST_ANCHOR_DIR, newValue);
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [WEBAUTHN_TRUST_ANCHOR_DIR]: "" });
  });

  it("renders an empty input and no warning when the key is missing", () => {
    const input: HTMLInputElement = fixture.nativeElement.querySelector("input");
    expect(input.value).toBe("");
    expect(fixture.nativeElement.querySelectorAll(".alert-warning").length).toBe(0);
  });

  it("warns about a relative path and about a trailing slash", () => {
    fixture.componentRef.setInput("formData", { [WEBAUTHN_TRUST_ANCHOR_DIR]: "relative/path/" });
    fixture.detectChanges();

    const warnings = Array.from(
      fixture.nativeElement.querySelectorAll(".alert-warning") as NodeListOf<HTMLElement>
    ).map((warning) => warning.textContent?.trim());

    expect(warnings).toEqual([
      "The trust_anchor_dir must be an absolute path.",
      'The trust_anchor_dir must not end with a "/".'
    ]);
  });
});
