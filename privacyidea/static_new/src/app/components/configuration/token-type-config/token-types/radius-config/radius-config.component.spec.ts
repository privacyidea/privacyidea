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
import { RadiusConfigComponent } from "@components/configuration/token-type-config/token-types/radius-config/radius-config.component";
import { provideRouter } from "@angular/router";
import { provideAnimations } from "@angular/platform-browser/animations";
import { RADIUS_SERVER } from "../../../../../constants/token.constants";

const mockRadiusServers = ["radius-server-1", "radius-server-2", "radius-server-3"];

describe("RadiusConfigComponent", () => {
  let fixture: ComponentFixture<RadiusConfigComponent>;
  let component: RadiusConfigComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RadiusConfigComponent],
      providers: [provideRouter([]), provideAnimations()]
    }).compileComponents();
    fixture = TestBed.createComponent(RadiusConfigComponent);
    fixture.componentRef.setInput("formData", {});
    fixture.componentRef.setInput("radiusServers", mockRadiusServers);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should emit formDataChange when updateFormData is called", () => {
    jest.spyOn(component.formDataChange, "emit");
    const newValue = "radius-server-1";
    component.updateFormData(RADIUS_SERVER, newValue);
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [RADIUS_SERVER]: newValue });
  });

  it("should display current formData value for radius identifier", () => {
    const testData = {
      [RADIUS_SERVER]: "radius-server-1"
    };
    fixture.componentRef.setInput("formData", testData);
    fixture.detectChanges();

    expect(component.formData()[RADIUS_SERVER]).toEqual("radius-server-1");
  });

  it("should handle empty radius identifier value", () => {
    jest.spyOn(component.formDataChange, "emit");
    const newValue = "";
    component.updateFormData(RADIUS_SERVER, newValue);
    expect(component.formDataChange.emit).toHaveBeenCalledWith({ [RADIUS_SERVER]: "" });
  });

  it("should handle radiusServers input correctly", () => {
    expect(component.radiusServers()).toEqual(mockRadiusServers);
    expect(component.radiusServers().length).toBe(3);
  });

  it("should handle empty radiusServers array", () => {
    fixture.componentRef.setInput("radiusServers", []);
    fixture.detectChanges();
    expect(component.radiusServers()).toEqual([]);
    expect(component.radiusServers().length).toBe(0);
  });

  it("should handle expanded input", () => {
    fixture.componentRef.setInput("expanded", true);
    fixture.detectChanges();
    expect(component.expanded()).toBe(true);

    fixture.componentRef.setInput("expanded", false);
    fixture.detectChanges();
    expect(component.expanded()).toBe(false);
  });

  it("should call updateFormData with empty value when clearField is called", async () => {
    const initialServer = "radius-server-1";
    fixture.componentRef.setInput("formData", { [RADIUS_SERVER]: initialServer });
    fixture.detectChanges();
    expect(component.formData()[RADIUS_SERVER]).toEqual(initialServer);

    jest.spyOn(component, "updateFormData");
    component.clearField(RADIUS_SERVER);
    expect(component.updateFormData).toHaveBeenCalledWith(RADIUS_SERVER, "");
  });
});

