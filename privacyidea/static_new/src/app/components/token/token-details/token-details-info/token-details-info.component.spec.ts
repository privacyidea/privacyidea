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

  it("saveInfo adds new key/value if provided, calls setTokenInfos, resets newInfo, turns off edit, and reloads", () => {
    const el = component.infoData()[0] as EditableElement<Record<string, string>>;
    expect(el.value).toEqual({ a: "1" });

    component.isEditingInfo.set(true);
    component.newInfo.set({ key: "b", value: "2" });
    tokenService.tokenSerial.set("SER");

    component.saveInfo(el);

    expect(el.value).toEqual({ a: "1", b: "2" });
    expect(tokenService.setTokenInfos).toHaveBeenCalledWith("SER", { a: "1", b: "2" });
    expect(component.newInfo()).toEqual({ key: "", value: "" });
    expect(component.isEditingInfo()).toBe(false);
    expect(tokenService.tokenDetailResource.reload).toHaveBeenCalledTimes(1);
  });

  it("saveInfo without new pair still calls setTokenInfos and reloads", () => {
    const el = component.infoData()[0] as EditableElement<Record<string, string>>;
    component.isEditingInfo.set(true);
    component.newInfo.set({ key: "", value: "" });
    tokenService.tokenSerial.set("SER");

    component.saveInfo(el);

    expect(el.value).toEqual({ a: "1" });
    expect(tokenService.setTokenInfos).toHaveBeenCalledWith("SER", { a: "1" });
    expect(tokenService.tokenDetailResource.reload).toHaveBeenCalledTimes(1);
    expect(component.isEditingInfo()).toBe(false);
  });

  it("template cast helpers pass values through and hide timestamp keys", () => {
    expect(component.asInfoMap(undefined)).toEqual({});
    expect(component.asInfoMap({ a: "1" })).toEqual({ a: "1" });

    const el = makeInfoEl({ a: "1" });
    expect(component.asInfoElement(el as unknown as EditableElement)).toBe(el);

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
});
