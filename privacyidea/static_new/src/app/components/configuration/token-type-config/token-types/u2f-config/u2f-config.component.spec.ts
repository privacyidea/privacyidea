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

describe("U2fConfigComponent", () => {
  let fixture: ComponentFixture<U2fConfigComponent>;
  let component: U2fConfigComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [U2fConfigComponent],
      providers: [provideRouter([])]
    }).compileComponents();
    fixture = TestBed.createComponent(U2fConfigComponent);
    fixture.componentRef.setInput("formData", {});
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should emit formDataChange when updateFormData is called", () => {
    jest.spyOn(component.formDataChange, "emit");
    component.updateFormData(U2F_APP_ID, "https://pi.server.com");
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [U2F_APP_ID]: "https://pi.server.com" });
  });

  it("renders an empty input and no warning when the key is missing", () => {
    const input: HTMLInputElement = fixture.nativeElement.querySelector("input");
    expect(input.value).toBe("");
    expect(fixture.nativeElement.querySelectorAll(".alert-warning").length).toBe(0);
  });

  it("shows the configured appId in the input", () => {
    fixture.componentRef.setInput("formData", { [U2F_APP_ID]: "https://pi.server.com" });
    fixture.detectChanges();

    const input: HTMLInputElement = fixture.nativeElement.querySelector("input");
    expect(input.value).toBe("https://pi.server.com");
    expect(fixture.nativeElement.querySelectorAll(".alert-warning").length).toBe(0);
  });

  it("warns about a non-https appId and about a trailing slash", () => {
    fixture.componentRef.setInput("formData", { [U2F_APP_ID]: "http://pi.server.com/" });
    fixture.detectChanges();

    const warnings = Array.from(
      fixture.nativeElement.querySelectorAll(".alert-warning") as NodeListOf<HTMLElement>
    ).map((warning) => warning.textContent?.trim());

    expect(warnings).toEqual(['The AppID needs to start with "https".', 'The AppID must not end with a "/".']);
  });
});
