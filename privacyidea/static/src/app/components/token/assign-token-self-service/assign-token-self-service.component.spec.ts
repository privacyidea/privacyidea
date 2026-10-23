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
import { provideHttpClient } from "@angular/common/http";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { Router } from "@angular/router";
import { ContentService } from "@services/content/content.service";
import { TokenService } from "@services/token/token.service";
import { MockContentService, MockRouter, MockTokenService } from "@testing/mock-services";
import { of } from "rxjs";
import { AssignTokenSelfServiceComponent } from "./assign-token-self-service.component";

describe("AssignTokenSelfServiceComponent (no zone.js)", () => {
  let fixture: ComponentFixture<AssignTokenSelfServiceComponent>;
  let component: AssignTokenSelfServiceComponent;

  let tokenService: MockTokenService;
  let routerMock: MockRouter;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AssignTokenSelfServiceComponent],
      providers: [
        provideHttpClient(),
        { provide: Router, useClass: MockRouter },
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(AssignTokenSelfServiceComponent);
    component = fixture.componentInstance;
    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    routerMock = TestBed.inject(Router) as unknown as MockRouter;
    tokenService.assignUser.mockReturnValue(of(null));

    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  const serialInput = (): HTMLInputElement => fixture.nativeElement.querySelector("mat-form-field input");
  const pinInputs = (): HTMLInputElement[] =>
    Array.from(fixture.nativeElement.querySelectorAll("app-enrollment-pin input"));
  const assignButton = (): HTMLButtonElement => fixture.nativeElement.querySelector(".enroll-button-container button");
  const typeInto = (input: HTMLInputElement, value: string) => {
    input.value = value;
    input.dispatchEvent(new Event("input"));
    fixture.detectChanges();
  };

  it("assignUserToToken: calls service, navigates to details, and updates tokenSerial", () => {
    const serial = "TKN-123";
    const pin = "1234";

    component.serialModel.set({ serial });
    component.setPinValue.set(pin);
    component.repeatPinValue.set(pin);

    component.assignUserToToken();

    expect(tokenService.assignUser).toHaveBeenCalledTimes(1);
    expect(tokenService.assignUser).toHaveBeenCalledWith({
      tokenSerial: serial,
      username: "",
      realm: "",
      pin
    });

    expect(routerMock.navigateByUrl).toHaveBeenCalledTimes(1);
    expect(routerMock.navigateByUrl).toHaveBeenCalledWith(expect.stringContaining(serial));
    expect(tokenService.tokenSerial()).toBe(serial);
  });

  it("starts with the Assign button disabled until a serial is entered", () => {
    expect(component.canAssign()).toBe(false);
    expect(assignButton().disabled).toBe(true);

    typeInto(serialInput(), "TKN-1");

    expect(component.serialModel().serial).toBe("TKN-1");
    expect(assignButton().disabled).toBe(false);
  });

  it("rejects a whitespace-only serial", () => {
    typeInto(serialInput(), "   ");
    expect(component.serialForm().valid()).toBe(false);
    expect(assignButton().disabled).toBe(true);
  });

  it("does not assign without a serial and shows the serial error", () => {
    component.assignUserToToken();
    fixture.detectChanges();

    expect(tokenService.assignUser).not.toHaveBeenCalled();
    expect(component.serialForm.serial().touched()).toBe(true);
    expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain("Serial is required");
  });

  it("does not assign when the repeated PIN differs and shows the mismatch", () => {
    component.serialModel.set({ serial: "TKN-1" });
    const [pin, repeat] = pinInputs();
    typeInto(pin, "1234");
    typeInto(repeat, "4321");

    expect(component.canAssign()).toBe(false);
    expect(assignButton().disabled).toBe(true);

    component.assignUserToToken();
    fixture.detectChanges();

    expect(tokenService.assignUser).not.toHaveBeenCalled();
    expect(fixture.nativeElement.querySelector("app-enrollment-pin mat-error")?.textContent).toContain(
      "PINs do not match."
    );
  });

  it("assigns with the typed PIN once both PIN fields match", () => {
    typeInto(serialInput(), "TKN-9");
    const [pin, repeat] = pinInputs();
    typeInto(pin, "5555");
    typeInto(repeat, "5555");

    expect(assignButton().disabled).toBe(false);
    assignButton().click();

    expect(tokenService.assignUser).toHaveBeenCalledWith(
      expect.objectContaining({ tokenSerial: "TKN-9", pin: "5555" })
    );
  });

  it("assigns without a PIN when both PIN fields are empty", () => {
    component.serialModel.set({ serial: "TKN-2" });
    component.assignUserToToken();
    expect(tokenService.assignUser).toHaveBeenCalledWith(expect.objectContaining({ tokenSerial: "TKN-2", pin: "" }));
  });
});
