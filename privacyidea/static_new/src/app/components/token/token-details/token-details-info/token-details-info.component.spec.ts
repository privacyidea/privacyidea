/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { signal, WritableSignal } from "@angular/core";

import { TokenDetailsInfoComponent } from "./token-details-info.component";
import { EditableElement } from "../../../shared/edit-buttons/edit-buttons.component";

import { TokenService } from "../../../../services/token/token.service";
import { OverflowService } from "../../../../services/overflow/overflow.service";
import { AuthService } from "../../../../services/auth/auth.service";

import {
  MockLocalService,
  MockNotificationService,
  MockOverflowService,
  MockTokenService
} from "../../../../../testing/mock-services";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MockAuthService } from "../../../../../testing/mock-services/mock-auth-service";

describe("TokenDetailsInfoComponent", () => {
  let component: TokenDetailsInfoComponent;
  let fixture: ComponentFixture<TokenDetailsInfoComponent>;
  let tokenSvc: MockTokenService;

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
      imports: [TokenDetailsInfoComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: OverflowService, useClass: MockOverflowService },
        { provide: AuthService, useClass: MockAuthService },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    // IMPORTANT: inject the mock instance so tokenSvc is not undefined
    tokenSvc = TestBed.inject(TokenService) as unknown as MockTokenService;

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
    expect(tokenSvc.tokenDetailResource.reload).not.toHaveBeenCalled();

    component.toggleInfoEdit();
    expect(component.isEditingInfo()).toBe(false);
    expect(tokenSvc.tokenDetailResource.reload).toHaveBeenCalledTimes(1);
  });

  it("saveInfo adds new key/value if provided, calls setTokenInfos, resets newInfo, turns off edit, and reloads", () => {
    const el = component.infoData()[0] as EditableElement<Record<string, string>>;
    expect(el.value).toEqual({ a: "1" });

    component.isEditingInfo.set(true);
    component.newInfo.set({ key: "b", value: "2" });
    tokenSvc.tokenSerial.set("SER");

    component.saveInfo(el);

    expect(el.value).toEqual({ a: "1", b: "2" });
    expect(tokenSvc.setTokenInfos).toHaveBeenCalledWith("SER", { a: "1", b: "2" });
    expect(component.newInfo()).toEqual({ key: "", value: "" });
    expect(component.isEditingInfo()).toBe(false);
    expect(tokenSvc.tokenDetailResource.reload).toHaveBeenCalledTimes(1);
  });

  it("saveInfo without new pair still calls setTokenInfos and reloads", () => {
    const el = component.infoData()[0] as EditableElement<Record<string, string>>;
    component.isEditingInfo.set(true);
    component.newInfo.set({ key: "", value: "" });
    tokenSvc.tokenSerial.set("SER");

    component.saveInfo(el);

    expect(el.value).toEqual({ a: "1" });
    expect(tokenSvc.setTokenInfos).toHaveBeenCalledWith("SER", { a: "1" });
    expect(tokenSvc.tokenDetailResource.reload).toHaveBeenCalledTimes(1);
    expect(component.isEditingInfo()).toBe(false);
  });

  it("deleteInfo calls service, marks info section as editing, and reloads", () => {
    component.isEditingInfo.set(false);
    tokenSvc.tokenSerial.set("SER");

    component.deleteInfo("a");

    expect(tokenSvc.deleteInfo).toHaveBeenCalledWith("SER", "a");
    expect(component.isEditingInfo()).toBe(true);
    expect(tokenSvc.tokenDetailResource.reload).toHaveBeenCalledTimes(1);
  });
});
