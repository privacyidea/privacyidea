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
import {
  YubikeyConfigComponent
} from "@components/configuration/token-type-config/token-types/yubikey-config/yubikey-config.component";
import { provideRouter } from "@angular/router";
import { provideAnimations } from "@angular/platform-browser/animations";

const mockYubikeyApiIds = ["yubikey.apiid.1", "yubikey.apiid.2", "yubikey.apiid.3"];

describe("YubikeyConfigComponent", () => {
  let fixture: ComponentFixture<YubikeyConfigComponent>;
  let component: YubikeyConfigComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [YubikeyConfigComponent],
      providers: [provideRouter([]), provideAnimations()]
    }).compileComponents();
    fixture = TestBed.createComponent(YubikeyConfigComponent);
    fixture.componentRef.setInput("formData", {});
    fixture.componentRef.setInput("yubikeyApiIds", mockYubikeyApiIds);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display current formData values", () => {
    const testData = {
      "yubikey.apiid.1": "apiKey1",
      "yubikey.apiid.2": "apiKey2",
      "yubikey.apiid.3": "apiKey3"
    };
    fixture.componentRef.setInput("formData", testData);
    fixture.detectChanges();

    expect(component.formData()["yubikey.apiid.1"]).toEqual("apiKey1");
    expect(component.formData()["yubikey.apiid.2"]).toEqual("apiKey2");
    expect(component.formData()["yubikey.apiid.3"]).toEqual("apiKey3");
  });

  it("should emit onYubikeyCreateNewKey when createNewKey is called with valid id", () => {
    jest.spyOn(component.onYubikeyCreateNewKey, "emit");
    const newId = "newClientId";
    component.newYubikeyApiId.set(newId);
    component.createNewKey();
    expect(component.onYubikeyCreateNewKey.emit).toHaveBeenCalledWith({apiId: newId, apiKey: "", generateKey: true});
  });

  it("should clear newYubikeyApiId and newYubikeyApiKey after creating a new key", () => {
    const newId = "clientId123";
    const newKey = "apiKey123";
    component.newYubikeyApiId.set(newId);
    component.newYubikeyApiKey.set(newKey);
    expect(component.newYubikeyApiId()).toBe(newId);
    expect(component.newYubikeyApiKey()).toBe(newKey);

    component.createNewKey();

    expect(component.newYubikeyApiId()).toBe("");
    expect(component.newYubikeyApiKey()).toBe("");
  });

  it("should not emit onYubikeyCreateNewKey when createNewKey is called with empty id", () => {
    jest.spyOn(component.onYubikeyCreateNewKey, "emit");
    component.newYubikeyApiId.set("");
    component.newYubikeyApiKey.set("apiKey");
    component.createNewKey();
    expect(component.onYubikeyCreateNewKey.emit).not.toHaveBeenCalled();
  });

  it("should emit onDeleteEntry when deleteEntry is called", () => {
    jest.spyOn(component.onDeleteEntry, "emit");
    const keyToDelete = "yubikey.apiid.1";
    component.deleteEntry(keyToDelete);
    expect(component.onDeleteEntry.emit).toHaveBeenCalledWith(keyToDelete);
  });

  it("should handle multiple yubikey API IDs", () => {
    const multipleIds = ["yubikey.apiid.1", "yubikey.apiid.2", "yubikey.apiid.3", "yubikey.apiid.4"];
    fixture.componentRef.setInput("yubikeyApiIds", multipleIds);
    fixture.detectChanges();
    expect(component.yubikeyApiIds().length).toBe(4);
  });

  it("should handle empty yubikeyApiIds array", () => {
    fixture.componentRef.setInput("yubikeyApiIds", []);
    fixture.detectChanges();
    expect(component.yubikeyApiIds().length).toBe(0);
  });

  it("should update newYubikeyApiId signal", () => {
    const newId = "testClientId";
    component.newYubikeyApiId.set(newId);
    expect(component.newYubikeyApiId()).toBe(newId);
  });

  it("should update newYubikeyApiKey signal", () => {
    const newKey = "testApiKey";
    component.newYubikeyApiKey.set(newKey);
    expect(component.newYubikeyApiKey()).toBe(newKey);
  });
});

