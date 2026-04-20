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
import { HotpConfigComponent } from "./hotp-config.component";
import { provideRouter } from "@angular/router";
import { HOTP_HASHLIB } from "../../../../../constants/token.constants";
import { provideAnimations } from "@angular/platform-browser/animations";

const mockHashLibs = ["sha1", "sha256", "sha512"];

describe("HotpConfigComponent", () => {
  let fixture: ComponentFixture<HotpConfigComponent>;
  let component: HotpConfigComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HotpConfigComponent],
      providers: [provideRouter([]), provideAnimations()]
    }).compileComponents();
    fixture = TestBed.createComponent(HotpConfigComponent);
    fixture.componentRef.setInput("formData", {});
    fixture.componentRef.setInput("hashLibs", mockHashLibs);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should emit formDataChange when updateFormData is called", () => {
    jest.spyOn(component.formDataChange, "emit");
    const newValue = "sha256";
    component.updateFormData(HOTP_HASHLIB, newValue);
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [HOTP_HASHLIB]: newValue });
  });

  it("should call updateFormData with empty value when clearField is called", async () => {
    const initialHashlib = "sha1";
    fixture.componentRef.setInput("formData", { [HOTP_HASHLIB]: initialHashlib });
    fixture.detectChanges();
    expect(component.formData()[HOTP_HASHLIB]).toEqual(initialHashlib);

    jest.spyOn(component, "updateFormData");
    component.clearField(HOTP_HASHLIB);
    expect(component.updateFormData).toHaveBeenCalledWith(HOTP_HASHLIB, "");
  });

  it("should preserve existing form data when updating a field", () => {
    const existingData = { "other.field": "value", [HOTP_HASHLIB]: "sha1" };
    fixture.componentRef.setInput("formData", existingData);
    fixture.detectChanges();

    jest.spyOn(component.formDataChange, "emit");
    const newHashlib = "sha256";
    component.updateFormData(HOTP_HASHLIB, newHashlib);

    expect(component.formDataChange.emit).toHaveBeenCalledWith({
      "other.field": "value",
      [HOTP_HASHLIB]: newHashlib
    });
  });
});
