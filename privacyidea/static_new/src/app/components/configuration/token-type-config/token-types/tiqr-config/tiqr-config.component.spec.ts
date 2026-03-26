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
import { TiqrConfigComponent } from "@components/configuration/token-type-config/token-types/tiqr-config/tiqr-config.component";
import { provideRouter } from "@angular/router";
import { provideAnimations } from "@angular/platform-browser/animations";
import {
  TIQR_AUTH_SERVER, TIQR_INFO_URL, TIQR_LOGO_URL, TIQR_OCRASUITE,
  TIQR_REG_SERVER,
  TIQR_SERVICE_DISPLAYNAME,
  TIQR_SERVICE_IDENTIFIER
} from "../../../../../constants/token.constants";

describe("TiqrConfigComponent", () => {
  let fixture: ComponentFixture<TiqrConfigComponent>;
  let component: TiqrConfigComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TiqrConfigComponent],
      providers: [provideRouter([]), provideAnimations()]
    }).compileComponents();
    fixture = TestBed.createComponent(TiqrConfigComponent);
    fixture.componentRef.setInput("formData", {});
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should emit formDataChange when updateFormData is called", () => {
    jest.spyOn(component.formDataChange, "emit");
    const newValue = "http://pi.server/ttype/tiqr";
    component.updateFormData(TIQR_REG_SERVER, newValue);
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [TIQR_REG_SERVER]: newValue });
  });

  it("should preserve existing formData when updating a field", () => {
    const initialData = {
      [TIQR_REG_SERVER]: "http://old.server/tiqr",
      [TIQR_SERVICE_DISPLAYNAME]: "Old Service"
    };
    fixture.componentRef.setInput("formData", initialData);
    fixture.detectChanges();

    jest.spyOn(component.formDataChange, "emit");
    const newValue = "http://new.server/tiqr";
    component.updateFormData(TIQR_REG_SERVER, newValue);

    expect(component.formDataChange.emit).toHaveBeenCalledWith({
      ...initialData,
      [TIQR_REG_SERVER]: newValue
    });
  });

  it("should display current formData values", () => {
    const testData = {
      [TIQR_REG_SERVER]: "http://pi.server/ttype/tiqr",
      [TIQR_AUTH_SERVER]: "http://auth.server/tiqr",
      [TIQR_SERVICE_DISPLAYNAME]: "Test Service",
      [TIQR_SERVICE_IDENTIFIER]: "org.privacyidea",
      [TIQR_LOGO_URL]: "https://pi.server/logo.png",
      [TIQR_INFO_URL]: "https://www.privacyidea.org",
      [TIQR_OCRASUITE]: "OCRA-1:HOTP-SHA1-6:QN10"
    };
    fixture.componentRef.setInput("formData", testData);
    fixture.detectChanges();

    expect(component.formData()[TIQR_REG_SERVER]).toEqual("http://pi.server/ttype/tiqr");
    expect(component.formData()[TIQR_AUTH_SERVER]).toEqual("http://auth.server/tiqr");
    expect(component.formData()[TIQR_SERVICE_DISPLAYNAME]).toEqual("Test Service");
    expect(component.formData()[TIQR_SERVICE_IDENTIFIER]).toEqual("org.privacyidea");
    expect(component.formData()[TIQR_LOGO_URL]).toEqual("https://pi.server/logo.png");
    expect(component.formData()[TIQR_INFO_URL]).toEqual("https://www.privacyidea.org");
    expect(component.formData()[TIQR_OCRASUITE]).toEqual("OCRA-1:HOTP-SHA1-6:QN10");
  });

  it("should handle empty field values", () => {
    jest.spyOn(component.formDataChange, "emit");
    
    component.updateFormData(TIQR_REG_SERVER, "");
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [TIQR_REG_SERVER]: "" });

    component.updateFormData(TIQR_SERVICE_DISPLAYNAME, "");
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [TIQR_SERVICE_DISPLAYNAME]: "" });
  });
});

