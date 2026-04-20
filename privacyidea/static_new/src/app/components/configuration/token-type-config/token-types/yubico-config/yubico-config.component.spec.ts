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
import { YubicoConfigComponent } from "@components/configuration/token-type-config/token-types/yubico-config/yubico-config.component";
import { provideRouter } from "@angular/router";
import { provideAnimations } from "@angular/platform-browser/animations";
import { YUBICO_ID, YUBICO_SECRET, YUBICO_URL } from "../../../../../constants/token.constants";

describe("YubicoConfigComponent", () => {
  let fixture: ComponentFixture<YubicoConfigComponent>;
  let component: YubicoConfigComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [YubicoConfigComponent],
      providers: [provideRouter([]), provideAnimations()]
    }).compileComponents();
    fixture = TestBed.createComponent(YubicoConfigComponent);
    fixture.componentRef.setInput("formData", {});
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should emit formDataChange when updateFormData is called", () => {
    jest.spyOn(component.formDataChange, "emit");
    const newValue = "12345";
    component.updateFormData(YUBICO_ID, newValue);
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [YUBICO_ID]: newValue });
  });

  it("should preserve existing formData when updating a field", () => {
    const initialData = {
      [YUBICO_ID]: "oldId",
      [YUBICO_SECRET]: "oldSecret"
    };
    fixture.componentRef.setInput("formData", initialData);
    fixture.detectChanges();

    jest.spyOn(component.formDataChange, "emit");
    const newValue = "newId";
    component.updateFormData(YUBICO_ID, newValue);

    expect(component.formDataChange.emit).toHaveBeenCalledWith({
      ...initialData,
      [YUBICO_ID]: newValue
    });
  });

  it("should display current formData values", () => {
    const testData = {
      [YUBICO_ID]: "12345",
      [YUBICO_SECRET]: "apiKeySecret",
      [YUBICO_URL]: "https://api.yubico.com/wsapi/2.0/verify"
    };
    fixture.componentRef.setInput("formData", testData);
    fixture.detectChanges();

    expect(component.formData()[YUBICO_ID]).toEqual("12345");
    expect(component.formData()[YUBICO_SECRET]).toEqual("apiKeySecret");
    expect(component.formData()[YUBICO_URL]).toEqual("https://api.yubico.com/wsapi/2.0/verify");
  });

  it("should handle empty field values", () => {
    jest.spyOn(component.formDataChange, "emit");
    
    component.updateFormData(YUBICO_ID, "");
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [YUBICO_ID]: "" });

    component.updateFormData(YUBICO_SECRET, "");
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [YUBICO_SECRET]: "" });
  });

  it("should handle expanded input", () => {
    fixture.componentRef.setInput("expanded", true);
    fixture.detectChanges();
    expect(component.expanded()).toBe(true);

    fixture.componentRef.setInput("expanded", false);
    fixture.detectChanges();
    expect(component.expanded()).toBe(false);
  });
});

