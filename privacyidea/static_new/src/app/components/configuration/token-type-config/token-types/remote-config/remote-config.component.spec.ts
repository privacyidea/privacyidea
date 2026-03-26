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
import { RemoteConfigComponent } from "@components/configuration/token-type-config/token-types/remote-config/remote-config.component";
import { provideRouter } from "@angular/router";
import { provideAnimations } from "@angular/platform-browser/animations";
import { REMOTE_SERVER, REMOTE_VERIFY_SSL } from "../../../../../constants/token.constants";

describe("RemoteConfigComponent", () => {
  let fixture: ComponentFixture<RemoteConfigComponent>;
  let component: RemoteConfigComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RemoteConfigComponent],
      providers: [provideRouter([]), provideAnimations()]
    }).compileComponents();
    fixture = TestBed.createComponent(RemoteConfigComponent);
    fixture.componentRef.setInput("formData", {});
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should emit formDataChange when updateFormData is called", () => {
    jest.spyOn(component.formDataChange, "emit");
    const newValue = "https://remote.privacyidea.server";
    component.updateFormData(REMOTE_SERVER, newValue);
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [REMOTE_SERVER]: newValue });
  });

  it("should preserve existing formData when updating remote server", () => {
    const initialData = {
      [REMOTE_VERIFY_SSL]: true,
      [REMOTE_SERVER]: "https://old.server.com"
    };
    fixture.componentRef.setInput("formData", initialData);
    fixture.detectChanges();

    jest.spyOn(component.formDataChange, "emit");
    const newValue = "https://new.server.com";
    component.updateFormData(REMOTE_SERVER, newValue);

    expect(component.formDataChange.emit).toHaveBeenCalledWith({
      ...initialData,
      [REMOTE_SERVER]: newValue
    });
  });

  it("should display current formData values", () => {
    const testData = {
      [REMOTE_SERVER]: "https://test.privacyidea.server",
      [REMOTE_VERIFY_SSL]: true
    };
    fixture.componentRef.setInput("formData", testData);
    fixture.detectChanges();

    expect(component.formData()[REMOTE_SERVER]).toEqual("https://test.privacyidea.server");
    expect(component.formData()[REMOTE_VERIFY_SSL]).toEqual(true);
  });

  it("should handle empty remote server value", () => {
    jest.spyOn(component.formDataChange, "emit");
    const newValue = "";
    component.updateFormData(REMOTE_SERVER, newValue);
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [REMOTE_SERVER]: "" });
  });

  it("should handle boolean values for verify SSL checkbox", () => {
    jest.spyOn(component.formDataChange, "emit");

    component.updateFormData(REMOTE_VERIFY_SSL, false);
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [REMOTE_VERIFY_SSL]: false });

    component.updateFormData(REMOTE_VERIFY_SSL, true);
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [REMOTE_VERIFY_SSL]: true });
  });

  it("should correctly compute verifySSL signal for strings", () => {
    fixture.componentRef.setInput("formData", { [REMOTE_VERIFY_SSL]: "0" });
    fixture.detectChanges();
    expect(component.verifySSL()).toBe(false);

    fixture.componentRef.setInput("formData", { [REMOTE_VERIFY_SSL]: "1" });
    fixture.detectChanges();
    expect(component.verifySSL()).toBe(true);
  });

  it("should correctly compute verifySSL signal for booleans", () => {
    fixture.componentRef.setInput("formData", { [REMOTE_VERIFY_SSL]: true });
    fixture.detectChanges();
    expect(component.verifySSL()).toBe(true);

    fixture.componentRef.setInput("formData", { [REMOTE_VERIFY_SSL]: false });
    fixture.detectChanges();
    expect(component.verifySSL()).toBe(false);
  });
});
