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
import { TotpConfigComponent } from "@components/configuration/token-type-config/token-types/totp-config/totp-config.component";
import { provideRouter } from "@angular/router";
import { provideAnimations } from "@angular/platform-browser/animations";
import {
  TOTP_HASHLIB,
  TOTP_TIME_SHIFT,
  TOTP_TIME_STEP,
  TOTP_TIME_WINDOW
} from "../../../../../constants/token.constants";

const mockTotpSteps = ["30", "60"];
const mockHashLibs = ["sha1", "sha256", "sha512"];

describe("TotpConfigComponent", () => {
  let fixture: ComponentFixture<TotpConfigComponent>;
  let component: TotpConfigComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TotpConfigComponent],
      providers: [provideRouter([]), provideAnimations()]
    }).compileComponents();
    fixture = TestBed.createComponent(TotpConfigComponent);
    fixture.componentRef.setInput("formData", {});
    fixture.componentRef.setInput("totpSteps", mockTotpSteps);
    fixture.componentRef.setInput("hashLibs", mockHashLibs);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should emit formDataChange when updateFormData is called", () => {
    jest.spyOn(component.formDataChange, "emit");
    const newValue = "60";
    component.updateFormData(TOTP_TIME_STEP, newValue);
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [TOTP_TIME_STEP]: newValue });
  });

  it("should preserve existing formData when updating a field", () => {
    const initialData = {
      [TOTP_TIME_STEP]: "30",
      [TOTP_TIME_WINDOW]: 180,
      [TOTP_HASHLIB]: "sha1"
    };
    fixture.componentRef.setInput("formData", initialData);
    fixture.detectChanges();

    jest.spyOn(component.formDataChange, "emit");
    const newTimeShift = 10;
    component.updateFormData(TOTP_TIME_SHIFT, newTimeShift);

    expect(component.formDataChange.emit).toHaveBeenCalledWith({
      ...initialData,
      [TOTP_TIME_SHIFT]: newTimeShift
    });
  });

  it("should display current formData values", () => {
    const testData = {
      [TOTP_TIME_STEP]: "60",
      [TOTP_TIME_WINDOW]: 240,
      [TOTP_TIME_SHIFT]: 5,
      [TOTP_HASHLIB]: "sha256"
    };
    fixture.componentRef.setInput("formData", testData);
    fixture.detectChanges();

    expect(component.formData()[TOTP_TIME_STEP]).toEqual("60");
    expect(component.formData()[TOTP_TIME_WINDOW]).toEqual(240);
    expect(component.formData()[TOTP_TIME_SHIFT]).toEqual(5);
    expect(component.formData()[TOTP_HASHLIB]).toEqual("sha256");
  });

  it("should call updateFormData with empty value when clearField is called", () => {
    const initialTimeStep = "60";
    fixture.componentRef.setInput("formData", { [TOTP_TIME_STEP]: initialTimeStep });
    fixture.detectChanges();
    expect(component.formData()[TOTP_TIME_STEP]).toEqual(initialTimeStep);

    jest.spyOn(component, "updateFormData");
    component.clearField(TOTP_TIME_STEP);
    expect(component.updateFormData).toHaveBeenCalledWith(TOTP_TIME_STEP, "");
  });
});

