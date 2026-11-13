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
import { WritableSignal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { MatSelect } from "@angular/material/select";
import { MatTooltip } from "@angular/material/tooltip";
import { MockTokenService } from "../../../../../testing/mock-services";
import { TokenService, TokenType } from "../../../../services/token/token.service";
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
    it("is named by its visible Token Type label", () => {
      const select: HTMLElement = fixture.nativeElement.querySelector("mat-select");
      const labelId = select.getAttribute("aria-labelledby")?.split(" ")[0] ?? "";
      const label = fixture.nativeElement.querySelector("mat-form-field label");

      expect(label?.textContent?.trim()).toBe("Token Type");
      expect(label?.id).toBe(labelId);
    });

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

    it("shows the reason on the enroll button while the enrollment is blocked", () => {
      fixture.componentRef.setInput("formInvalid", true);
      fixture.componentRef.setInput("enrollBlockedReason", "needs privacyideaserver_read");
      fixture.detectChanges();
      const button: HTMLButtonElement = fixture.nativeElement.querySelector("button[type='submit']");
      const tooltip: MatTooltip = fixture.debugElement
        .queryAll(By.directive(MatTooltip))
        .find((el) => el.nativeElement.contains(button))!
        .injector.get(MatTooltip);
      expect(tooltip.message).toBe("needs privacyideaserver_read");
      expect(tooltip.disabled).toBe(false);
    });

    it("shows no tooltip on the enroll button without a blocking reason", () => {
      const button: HTMLButtonElement = fixture.nativeElement.querySelector("button[type='submit']");
      const tooltip: MatTooltip = fixture.debugElement
        .queryAll(By.directive(MatTooltip))
        .find((el) => el.nativeElement.contains(button))!
        .injector.get(MatTooltip);
      expect(tooltip.disabled).toBe(true);
    });

    it("enroll button is enabled when form is valid and a token type is selected", () => {
      fixture.componentRef.setInput("formInvalid", false);
      fixture.detectChanges();
      const button: HTMLButtonElement = fixture.nativeElement.querySelector("button[type='submit']");
      expect(button.disabled).toBe(false);
    });
  });

  describe("unsupported token types", () => {
    const supportedType: TokenType = { key: "hotp", name: "HOTP", info: "HOTP: counter based", text: "" };
    const unsupportedType = { key: "customtoken", name: "Custom", info: "", text: "" } as unknown as TokenType;

    const openOptions = (): HTMLElement[] => {
      (tokenService.tokenTypeOptions as unknown as WritableSignal<TokenType[]>).set([supportedType, unsupportedType]);
      fixture.detectChanges();
      const selectInstance: MatSelect = fixture.debugElement.query(By.directive(MatSelect)).componentInstance;
      selectInstance.open();
      fixture.detectChanges();
      return Array.from(document.querySelectorAll<HTMLElement>("mat-option"));
    };

    it("renders an unsupported type as a disabled option with the info icon and a supported one as enabled without it", () => {
      const [supportedOption, unsupportedOption] = openOptions();
      expect(unsupportedOption.classList.contains("select-option-unsupported")).toBe(true);
      expect(unsupportedOption.getAttribute("aria-disabled")).toBe("true");
      expect(unsupportedOption.querySelector(".select-option-unsupported-icon mat-icon")?.textContent).toContain(
        "info_outline"
      );
      expect(supportedOption.classList.contains("select-option-unsupported")).toBe(false);
      expect(supportedOption.getAttribute("aria-disabled")).toBe("false");
      expect(supportedOption.querySelector(".select-option-unsupported-icon")).toBeNull();
    });

    it("uses the unsupported hint as tooltip only for the unsupported type", () => {
      openOptions();
      const messages = fixture.debugElement
        .queryAll(By.directive(MatTooltip))
        .map((element) => element.injector.get(MatTooltip).message);
      expect(messages).toContain(component["unsupportedTypeHint"]);
      expect(messages.filter((message) => message === component["unsupportedTypeHint"])).toHaveLength(1);
      expect(messages).toContain("counter based");
    });

    it("takes the option label from tokenTypeDisplayLabel", () => {
      const colonSupported: TokenType = { key: "hotp", name: "Hotp key", info: "HOTP: counter based", text: "" };
      const colonUnsupported = {
        key: "customtoken",
        name: "Custom name",
        info: "Special: something else",
        text: ""
      } as unknown as TokenType;
      const noColonUnsupported = {
        key: "othertoken",
        name: "Other name",
        info: "no colon here",
        text: ""
      } as unknown as TokenType;
      (tokenService.tokenTypeOptions as unknown as WritableSignal<TokenType[]>).set([
        colonSupported,
        colonUnsupported,
        noColonUnsupported
      ]);
      fixture.detectChanges();
      const selectInstance: MatSelect = fixture.debugElement.query(By.directive(MatSelect)).componentInstance;
      selectInstance.open();
      fixture.detectChanges();
      const labels = Array.from(document.querySelectorAll<HTMLElement>("mat-option")).map((option) =>
        option.querySelector(".select-option-label")?.textContent?.trim()
      );
      expect(labels).toEqual(["HOTP", "Special", "Other name"]);
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
