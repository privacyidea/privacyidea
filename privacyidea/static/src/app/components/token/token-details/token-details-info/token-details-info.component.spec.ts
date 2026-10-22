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
import { signal, WritableSignal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";

import { EditableElement } from "@components/shared/edit-buttons/edit-buttons.component";
import { TokenDetailsInfoComponent } from "./token-details-info.component";

import { AuthService } from "@services/auth/auth.service";
import { TokenService } from "@services/token/token.service";

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MockLocalService, MockNotificationService, MockTokenService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";

describe("TokenDetailsInfoComponent", () => {
  let component: TokenDetailsInfoComponent;
  let fixture: ComponentFixture<TokenDetailsInfoComponent>;
  let tokenService: MockTokenService;

  const makeInfoEl = (value: Record<string, string>): EditableElement<Record<string, string>> => ({
    keyMap: { key: "info" },
    isEditing: signal(false),
    value
  });

  const makeDetailEl = (key: string, value: unknown): EditableElement => ({
    keyMap: { key },
    isEditing: signal(false),
    value
  });

  beforeEach(async () => {
    jest.clearAllMocks();

    await TestBed.configureTestingModule({
      imports: [TokenDetailsInfoComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: AuthService, useClass: MockAuthService },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    // IMPORTANT: inject the mock instance so tokenService is not undefined
    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;

    fixture = TestBed.createComponent(TokenDetailsInfoComponent);
    component = fixture.componentInstance;

    const infoArr: EditableElement<Record<string, string>>[] = [makeInfoEl({ a: "1" })];
    const detailArr: EditableElement[] = [makeDetailEl("info", {})];

    component.infoData = signal(infoArr as unknown as EditableElement[]) as WritableSignal<EditableElement[]>;
    component.detailData = signal(detailArr as unknown as EditableElement[]) as WritableSignal<EditableElement[]>;
    component.isAnyEditingOrRevoked = signal(false);
    component.isEditingInfo = signal(false);
    component.isEditingUser = signal(false);

    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("toggleInfoEdit flips the flag; reloads when turning off edit mode", () => {
    expect(component.isEditingInfo()).toBe(false);

    component.toggleInfoEdit();
    expect(component.isEditingInfo()).toBe(true);
    expect(tokenService.tokenDetailResource.reload).not.toHaveBeenCalled();

    component.toggleInfoEdit();
    expect(component.isEditingInfo()).toBe(false);
    expect(tokenService.tokenDetailResource.reload).toHaveBeenCalledTimes(1);
  });

  it("saveInfo sends the new key/value, resets newInfo, turns off edit, and reloads", () => {
    const el = component.infoData()[0] as EditableElement<Record<string, string>>;
    expect(el.value).toEqual({ a: "1" });

    component.isEditingInfo.set(true);
    component.newInfo.set({ key: "b", value: "2" });
    tokenService.tokenSerial.set("SER");

    component.saveInfo(el);

    expect(el.value).toEqual({ a: "1" });
    expect(tokenService.setTokenInfos).toHaveBeenCalledWith("SER", { b: "2" }, [], []);
    expect(component.newInfo()).toEqual({ key: "", value: "" });
    expect(component.isEditingInfo()).toBe(false);
    expect(tokenService.tokenDetailResource.reload).toHaveBeenCalledTimes(1);
  });

  it("saveInfo trims the new key", () => {
    const el = component.infoData()[0] as EditableElement<Record<string, string>>;
    component.isEditingInfo.set(true);
    component.newInfo.set({ key: " b ", value: "2" });

    component.saveInfo(el);

    expect(tokenService.setTokenInfos).toHaveBeenCalledWith(expect.anything(), { b: "2" }, [], []);
  });

  it("saveInfo without new pair sends nothing but still reloads", () => {
    const el = component.infoData()[0] as EditableElement<Record<string, string>>;
    component.isEditingInfo.set(true);
    component.newInfo.set({ key: "", value: "" });
    tokenService.tokenSerial.set("SER");

    component.saveInfo(el);

    expect(el.value).toEqual({ a: "1" });
    expect(tokenService.setTokenInfos).toHaveBeenCalledWith("SER", {}, [], []);
    expect(tokenService.tokenDetailResource.reload).toHaveBeenCalledTimes(1);
    expect(component.isEditingInfo()).toBe(false);
  });

  it("marks the entries the token maintains as not editable and not deletable", () => {
    component.readonlyInfoKeys = signal(["tokenkind", "refilltoken", "hashlib"]);
    component.undeletableInfoKeys = signal(["tokenkind", "hashlib"]);
    component.settableInfoKeys = signal(["hashlib"]);

    // An entry the token maintains is shown, but neither editable nor deletable
    expect(component.isInfoKeyEditable("tokenkind")).toBe(false);
    expect(component.isInfoKeyDeletable("tokenkind")).toBe(false);
    // A refill token cannot be changed, but deleting it revokes the offline refill and is allowed
    expect(component.isInfoKeyEditable("refilltoken")).toBe(false);
    expect(component.isInfoKeyDeletable("refilltoken")).toBe(true);
    // An entry with its own endpoint stays editable through that endpoint
    expect(component.isInfoKeyEditable("hashlib")).toBe(true);
    // Free-form metadata is unrestricted
    expect(component.isInfoKeyEditable("a note")).toBe(true);
    expect(component.isInfoKeyDeletable("a note")).toBe(true);
  });

  it("saveInfo passes the keys the token maintains on to the service", () => {
    const el = component.infoData()[0] as EditableElement<Record<string, string>>;
    component.readonlyInfoKeys = signal(["tokenkind"]);
    component.settableInfoKeys = signal(["hashlib"]);
    component.isEditingInfo.set(true);
    tokenService.tokenSerial.set("SER");

    component.saveInfo(el);

    expect(tokenService.setTokenInfos).toHaveBeenCalledWith("SER", {}, ["tokenkind"], ["hashlib"]);
  });

  it("template cast helper passes values through and hides timestamp keys", () => {
    expect(component.asInfoMap(undefined)).toEqual({});
    expect(component.asInfoMap({ a: "1" })).toEqual({ a: "1" });

    expect(component.visibleInfoKeys({ a: "1", creation_date: "x", assignment_date: "y", last_auth: "z" })).toEqual([
      "a"
    ]);
  });

  it("deleteInfo calls service, marks info section as editing, and reloads", () => {
    component.isEditingInfo.set(false);
    tokenService.tokenSerial.set("SER");

    component.deleteInfo("a");

    expect(tokenService.deleteInfo).toHaveBeenCalledWith("SER", "a");
    expect(component.isEditingInfo()).toBe(true);
    expect(tokenService.tokenDetailResource.reload).toHaveBeenCalledTimes(1);
  });

  describe("editing the entries", () => {
    const textareas = (): HTMLTextAreaElement[] =>
      Array.from(fixture.nativeElement.querySelectorAll(".info-edit-field textarea"));
    const addRow = () => fixture.nativeElement.querySelector(".info-add-row") as HTMLElement;
    const type = (el: HTMLInputElement | HTMLTextAreaElement, value: string) => {
      el.value = value;
      el.dispatchEvent(new Event("input"));
      fixture.detectChanges();
    };
    const startEditing = () => {
      (TestBed.inject(AuthService) as unknown as MockAuthService).authData.set({
        ...MockAuthService.MOCK_AUTH_DATA,
        rights: ["settokeninfo"]
      });
      component.isAnyEditingOrRevoked = signal(true);
      component.isEditingInfo.set(true);
      fixture.detectChanges();
    };
    const saveButton = () => fixture.nativeElement.querySelector("button[aria-label='Save']") as HTMLButtonElement;

    it("shows one input per entry, filled with the value of the token", () => {
      startEditing();
      expect(textareas().map((t) => t.value)).toEqual(["1"]);
    });

    it("writes typed values to the draft and leaves the value of the token untouched", () => {
      startEditing();
      type(textareas()[0], "changed");

      expect(component["infoDraft"]()).toEqual({ a: "changed" });
      expect((component.infoData()[0] as EditableElement<Record<string, string>>).value).toEqual({ a: "1" });
    });

    it("sends only the entries that were edited", () => {
      const el = component.infoData()[0] as EditableElement<Record<string, string>>;
      el.value = { a: "1", b: "2" };
      component.infoData.set([el as unknown as EditableElement]);
      tokenService.tokenSerial.set("SER");
      startEditing();
      expect(textareas().map((t) => t.value)).toEqual(["1", "2"]);

      type(textareas()[1], "edited");
      component.saveInfo(el);

      expect(tokenService.setTokenInfos).toHaveBeenCalledWith("SER", { b: "edited" }, [], []);
    });

    it("takes the draft from the reloaded values and drops what was typed", () => {
      startEditing();
      type(textareas()[0], "changed");

      component.infoData.set([makeInfoEl({ a: "reloaded" }) as unknown as EditableElement]);
      fixture.detectChanges();

      expect(component["infoDraft"]()).toEqual({ a: "reloaded" });
      expect(textareas()[0].value).toBe("reloaded");
    });

    it("starts from the values of the token again after cancelling", () => {
      startEditing();
      type(textareas()[0], "changed");

      component.toggleInfoEdit();
      fixture.detectChanges();
      startEditing();

      expect(textareas()[0].value).toBe("1");
    });

    it("can be saved while the add row is empty", () => {
      startEditing();
      expect(component.canSave()).toBe(true);
      expect(saveButton().disabled).toBe(false);
    });

    it("is always saveable when not editing", () => {
      component.newInfo.set({ key: "", value: "x" });
      expect(component.canSave()).toBe(true);
    });

    it("blocks Save and shows an error while a value is given without a key", () => {
      startEditing();
      const [valueInput] = Array.from(addRow().querySelectorAll("textarea"));
      type(valueInput, "x");
      valueInput.dispatchEvent(new Event("blur"));
      const keyInput = addRow().querySelector("input") as HTMLInputElement;
      keyInput.dispatchEvent(new Event("blur"));
      fixture.detectChanges();

      expect(component.canSave()).toBe(false);
      expect(saveButton().disabled).toBe(true);
      expect(addRow().textContent).toContain("Key is required.");
    });

    it("blocks Save and shows an error while a key is given without a value", () => {
      startEditing();
      const keyInput = addRow().querySelector("input") as HTMLInputElement;
      type(keyInput, "c");
      keyInput.dispatchEvent(new Event("blur"));
      const valueInput = addRow().querySelector("textarea") as HTMLTextAreaElement;
      valueInput.dispatchEvent(new Event("blur"));
      fixture.detectChanges();

      expect(component.canSave()).toBe(false);
      expect(addRow().textContent).toContain("Value is required.");
    });

    it("rejects a key that already exists", () => {
      startEditing();
      const keyInput = addRow().querySelector("input") as HTMLInputElement;
      type(keyInput, "a");
      type(addRow().querySelector("textarea") as HTMLTextAreaElement, "x");
      keyInput.dispatchEvent(new Event("blur"));
      fixture.detectChanges();

      expect(component.canSave()).toBe(false);
      expect(addRow().textContent).toContain("This key already exists.");
    });

    it("saveInfo sends nothing and touches the add row while it is incomplete", () => {
      startEditing();
      component.newInfo.set({ key: "", value: "x" });
      const el = component.infoData()[0] as EditableElement<Record<string, string>>;

      component.saveInfo(el);

      expect(tokenService.setTokenInfos).not.toHaveBeenCalled();
      expect(component.isEditingInfo()).toBe(true);
      expect(component["newInfoForm"].key().touched()).toBe(true);
      expect(component["newInfoForm"].value().touched()).toBe(true);
    });
  });
});
