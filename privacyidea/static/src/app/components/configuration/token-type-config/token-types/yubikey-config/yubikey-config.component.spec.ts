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
import { YubikeyConfigComponent } from "@components/configuration/token-type-config/token-types/yubikey-config/yubikey-config.component";
import { createTokenTypeConfigForm } from "@testing/token-type-config-form";

const mockYubikeyApiIds = ["yubikey.apiid.1", "yubikey.apiid.2", "yubikey.apiid.3"];
const mockConfig = () => ({ "yubikey.apiid.1": "apiKey1", "yubikey.apiid.2": "apiKey2", "yubikey.apiid.3": "apiKey3" });

describe("YubikeyConfigComponent", () => {
  let fixture: ComponentFixture<YubikeyConfigComponent>;
  let component: YubikeyConfigComponent;
  let configForm: ReturnType<typeof createTokenTypeConfigForm>;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const idInput = () => fixture.nativeElement.querySelector('input[placeholder="Client ID"]') as HTMLInputElement;
  const keyInput = () => fixture.nativeElement.querySelector('input[placeholder="API Key"]') as HTMLInputElement;
  const generateCheckbox = () => fixture.nativeElement.querySelector("mat-checkbox input") as HTMLInputElement;
  const addButton = () => fixture.nativeElement.querySelector("button.action-button-secondary") as HTMLButtonElement;
  const errors = () =>
    Array.from(fixture.nativeElement.querySelectorAll("mat-error") as NodeListOf<HTMLElement>).map((error) =>
      error.textContent?.trim()
    );
  const type = async (element: HTMLInputElement, value: string) => {
    element.value = value;
    element.dispatchEvent(new Event("input"));
    await flush();
  };

  const create = async (config: Record<string, string> = mockConfig(), apiIds: string[] = mockYubikeyApiIds) => {
    configForm = createTokenTypeConfigForm(config);
    fixture = TestBed.createComponent(YubikeyConfigComponent);
    fixture.componentRef.setInput("config", configForm.form);
    fixture.componentRef.setInput("yubikeyApiIds", apiIds);
    component = fixture.componentInstance;
    await flush();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [YubikeyConfigComponent],
      providers: [provideRouter([])]
    }).compileComponents();
  });

  it("should create", async () => {
    await create();
    expect(component).toBeTruthy();
  });

  it("lists the API IDs with the keys of the form", async () => {
    await create();

    const rows = Array.from(fixture.nativeElement.querySelectorAll("tbody tr") as NodeListOf<HTMLElement>).map((row) =>
      Array.from(row.querySelectorAll("td"))
        .slice(0, 2)
        .map((cell) => cell.textContent?.trim())
    );
    expect(rows).toEqual([
      ["yubikey.apiid.1", "apiKey1"],
      ["yubikey.apiid.2", "apiKey2"],
      ["yubikey.apiid.3", "apiKey3"]
    ]);
  });

  it("should emit deleteRequest when deleteEntry is called", async () => {
    await create();
    jest.spyOn(component.deleteRequest, "emit");
    const keyToDelete = "yubikey.apiid.1";
    component.deleteEntry(keyToDelete);
    expect(component.deleteRequest.emit).toHaveBeenCalledWith(keyToDelete);
  });

  it("should handle multiple and no yubikey API IDs", async () => {
    await create({ ...mockConfig(), "yubikey.apiid.4": "k" }, [...mockYubikeyApiIds, "yubikey.apiid.4"]);
    expect(component.yubikeyApiIds().length).toBe(4);

    fixture.componentRef.setInput("yubikeyApiIds", []);
    fixture.detectChanges();
    expect(component.yubikeyApiIds().length).toBe(0);
  });

  describe("new key", () => {
    beforeEach(async () => {
      await create({}, []);
    });

    it("starts with the Add button disabled and no error", () => {
      expect(addButton().disabled).toBe(true);
      expect(errors()).toEqual([]);
      expect(generateCheckbox().checked).toBe(true);
      expect(keyInput().disabled).toBe(true);
    });

    it("enables the Add button for a valid client ID", async () => {
      await type(idInput(), "newClientId");

      expect(component.newKey().apiId).toBe("newClientId");
      expect(addButton().disabled).toBe(false);
    });

    it("shows the required error once the empty client ID was touched", async () => {
      await type(idInput(), "x");
      await type(idInput(), "");
      component.newKeyForm.apiId().markAsTouched();
      await flush();

      expect(errors()).toEqual(["Client ID is required."]);
      expect(addButton().disabled).toBe(true);
    });

    it("rejects a client ID with characters other than alphanumerics, dots, underscores and hyphens", async () => {
      await type(idInput(), "bad id!");
      component.newKeyForm.apiId().markAsTouched();
      await flush();

      expect(errors()).toEqual(["Invalid characters. Only alphanumeric, dots, underscores and hyphens are allowed."]);
      expect(addButton().disabled).toBe(true);
    });

    it("accepts alphanumerics, dots, underscores and hyphens", async () => {
      await type(idInput(), "Az09._-");
      expect(component.newKeyForm().valid()).toBe(true);
    });

    it("enables the API key input once the key is no longer generated", async () => {
      generateCheckbox().click();
      await flush();

      expect(component.newKey().generateKey).toBe(false);
      expect(keyInput().disabled).toBe(false);

      await type(keyInput(), "typedKey");
      expect(component.newKey().apiKey).toBe("typedKey");
    });

    it("emits the new key and clears the id and key after a click on Add", async () => {
      jest.spyOn(component.yubikeyCreateNewKey, "emit");
      generateCheckbox().click();
      await flush();
      await type(idInput(), "clientId123");
      await type(keyInput(), "apiKey123");

      addButton().click();
      await flush();

      expect(component.yubikeyCreateNewKey.emit).toHaveBeenCalledWith({
        apiId: "clientId123",
        apiKey: "apiKey123",
        generateKey: false
      });
      expect(component.newKey()).toEqual({ apiId: "", apiKey: "", generateKey: false });
      expect(idInput().value).toBe("");
      expect(errors()).toEqual([]);
      expect(component.newKeyForm().touched()).toBe(false);
    });

    it("emits a generated key request with the id", async () => {
      jest.spyOn(component.yubikeyCreateNewKey, "emit");
      await type(idInput(), "newClientId");

      component.createNewKey();

      expect(component.yubikeyCreateNewKey.emit).toHaveBeenCalledWith({
        apiId: "newClientId",
        apiKey: "",
        generateKey: true
      });
    });

    it("does not emit for an empty or invalid client ID", async () => {
      jest.spyOn(component.yubikeyCreateNewKey, "emit");

      component.createNewKey();
      await type(idInput(), "bad id!");
      component.createNewKey();

      expect(component.yubikeyCreateNewKey.emit).not.toHaveBeenCalled();
    });
  });
});
