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
import { By } from "@angular/platform-browser";
import { MatSelect } from "@angular/material/select";
import { MockTokenService } from "../../../../../testing/mock-services";
import { TokenService } from "../../../../services/token/token.service";
import { TokenEnrollmentTypeSelectorComponent } from "./token-enrollment-type-selector.component";

describe("TokenEnrollmentTypeSelectorComponent", () => {
  let fixture: ComponentFixture<TokenEnrollmentTypeSelectorComponent>;
  let component: TokenEnrollmentTypeSelectorComponent;
  let tokenService: MockTokenService;
  let scrollEl: HTMLDivElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenEnrollmentTypeSelectorComponent],
      providers: [{ provide: TokenService, useClass: MockTokenService }]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenEnrollmentTypeSelectorComponent);
    component = fixture.componentInstance;
    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;

    scrollEl = document.createElement("div");
    fixture.componentRef.setInput("scrollContainer", scrollEl);
    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  describe("token type select", () => {
    it("renders one option per token type", () => {
      const selectInstance: MatSelect = fixture.debugElement.query(By.directive(MatSelect)).componentInstance;
      expect(selectInstance.options.length).toBe(tokenService.tokenTypeOptions().length);
    });

    it("enroll button is disabled when formInvalid is true", () => {
      fixture.componentRef.setInput("formInvalid", true);
      fixture.detectChanges();
      const button: HTMLButtonElement = fixture.nativeElement.querySelector("button[type='submit']");
      expect(button.disabled).toBe(true);
    });

    it("enroll button is enabled when form is valid and a token type is selected", () => {
      fixture.componentRef.setInput("formInvalid", false);
      fixture.detectChanges();
      const button: HTMLButtonElement = fixture.nativeElement.querySelector("button[type='submit']");
      expect(button.disabled).toBe(false);
    });

    it("enroll button is disabled when no token type is selected", () => {
      (tokenService.selectedTokenType as any).set(null);
      fixture.detectChanges();
      const button: HTMLButtonElement = fixture.nativeElement.querySelector("button[type='submit']");
      expect(button.disabled).toBe(true);
    });
  });

  describe("reopen dialog button", () => {
    it("has 'hidden' class when canReopenDialog is false", () => {
      fixture.componentRef.setInput("canReopenDialog", false);
      fixture.detectChanges();
      const button: HTMLButtonElement = fixture.nativeElement.querySelector("button[type='button']");
      expect(button.classList.contains("hidden")).toBe(true);
    });

    it("does not have 'hidden' class when canReopenDialog is true", () => {
      fixture.componentRef.setInput("canReopenDialog", true);
      fixture.detectChanges();
      const button: HTMLButtonElement = fixture.nativeElement.querySelector("button[type='button']");
      expect(button.classList.contains("hidden")).toBe(false);
    });

    it("emits reopenDialog when clicked", () => {
      fixture.componentRef.setInput("canReopenDialog", true);
      fixture.detectChanges();

      const emitSpy = jest.fn();
      const sub = component.reopenDialog.subscribe(emitSpy);

      fixture.nativeElement.querySelector("button[type='button']").click();

      expect(emitSpy).toHaveBeenCalledTimes(1);
      sub.unsubscribe();
    });
  });
});
