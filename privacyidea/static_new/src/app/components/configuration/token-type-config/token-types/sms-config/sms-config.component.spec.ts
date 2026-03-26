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
import { SmsConfigComponent } from "@components/configuration/token-type-config/token-types/sms-config/sms-config.component";
import { provideRouter } from "@angular/router";
import { provideAnimations } from "@angular/platform-browser/animations";
import { SMS_GATEWAY, SMS_PROVIDER_TIMEOUT } from "../../../../../constants/token.constants";

const mockSmsGateways = ["gateway1", "gateway2", "gateway3"];

describe("SmsConfigComponent", () => {
  let fixture: ComponentFixture<SmsConfigComponent>;
  let component: SmsConfigComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SmsConfigComponent],
      providers: [provideRouter([]), provideAnimations()]
    }).compileComponents();
    fixture = TestBed.createComponent(SmsConfigComponent);
    fixture.componentRef.setInput("formData", {});
    fixture.componentRef.setInput("smsGateways", mockSmsGateways);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should emit formDataChange when updateFormData is called", () => {
    jest.spyOn(component.formDataChange, "emit");
    const newValue = "gateway1";
    component.updateFormData(SMS_GATEWAY, newValue);
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [SMS_GATEWAY]: newValue });
  });

  it("should preserve existing formData when updating SMS gateway", () => {
    const initialData = {
      "some.other.key": "value",
      [SMS_GATEWAY]: "gateway1"
    };
    fixture.componentRef.setInput("formData", initialData);
    fixture.detectChanges();

    jest.spyOn(component.formDataChange, "emit");
    const newValue = "gateway2";
    component.updateFormData(SMS_GATEWAY, newValue);

    expect(component.formDataChange.emit).toHaveBeenCalledWith({
      ...initialData,
      [SMS_GATEWAY]: newValue
    });
  });

  it("should display current formData values", () => {
    const testData = {
      [SMS_GATEWAY]: "gateway2",
      [SMS_PROVIDER_TIMEOUT]: 450
    };
    fixture.componentRef.setInput("formData", testData);
    fixture.detectChanges();

    expect(component.formData()[SMS_GATEWAY]).toEqual("gateway2");
    expect(component.formData()[SMS_PROVIDER_TIMEOUT]).toEqual(450);
  });

  it("should call updateFormData with empty value when clearField is called", () => {
    const initialGateway = "gateway1";
    fixture.componentRef.setInput("formData", { [SMS_GATEWAY]: initialGateway });
    fixture.detectChanges();
    expect(component.formData()[SMS_GATEWAY]).toEqual(initialGateway);

    jest.spyOn(component, "updateFormData");
    component.clearField(SMS_GATEWAY);
    expect(component.updateFormData).toHaveBeenCalledWith(SMS_GATEWAY, "");
  });

  it("should handle empty SMS identifier value", () => {
    jest.spyOn(component.formDataChange, "emit");
    const newValue = "";
    component.updateFormData(SMS_GATEWAY, newValue);
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [SMS_GATEWAY]: "" });
  });

  it("should handle smsGateways input correctly", () => {
    expect(component.smsGateways()).toEqual(mockSmsGateways);
    expect(component.smsGateways().length).toBe(3);
  });

  it("should handle expanded input", () => {
    fixture.componentRef.setInput("expanded", true);
    fixture.detectChanges();
    expect(component.expanded()).toBe(true);

    fixture.componentRef.setInput("expanded", false);
    fixture.detectChanges();
    expect(component.expanded()).toBe(false);
  });

  it("should handle numeric values for provider timeout", () => {
    jest.spyOn(component.formDataChange, "emit");
    
    component.updateFormData(SMS_PROVIDER_TIMEOUT, 100);
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [SMS_PROVIDER_TIMEOUT]: 100 });

    component.updateFormData(SMS_PROVIDER_TIMEOUT, 500);
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [SMS_PROVIDER_TIMEOUT]: 500 });
  });
});
