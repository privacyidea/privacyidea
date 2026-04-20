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
import { DaypasswordConfigComponent } from "./daypassword-config.component";
import { DAYPASSWORD_HASHLIB } from "../../../../../constants/token.constants";
import { provideAnimations } from "@angular/platform-browser/animations";

const mockHashLibs = ["sha1", "sha256", "sha512"];

describe("DaypasswordConfigComponent", () => {
  let fixture: ComponentFixture<DaypasswordConfigComponent>;
  let component: DaypasswordConfigComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DaypasswordConfigComponent],
      providers: [provideAnimations()]
    }).compileComponents();
    fixture = TestBed.createComponent(DaypasswordConfigComponent);
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
    component.updateFormData(DAYPASSWORD_HASHLIB, newValue);
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [DAYPASSWORD_HASHLIB]: newValue });
  });

  it("should call updateFormData with empty value when clearField is called", async () => {
    const initialHashlib = "sha256";
    fixture.componentRef.setInput("formData", { [DAYPASSWORD_HASHLIB]: initialHashlib });
    fixture.detectChanges();
    expect(component.formData()[DAYPASSWORD_HASHLIB]).toEqual(initialHashlib);

    jest.spyOn(component, "updateFormData");
    component.clearField(DAYPASSWORD_HASHLIB);
    expect(component.updateFormData).toHaveBeenCalledWith(DAYPASSWORD_HASHLIB, "");
  });
});
