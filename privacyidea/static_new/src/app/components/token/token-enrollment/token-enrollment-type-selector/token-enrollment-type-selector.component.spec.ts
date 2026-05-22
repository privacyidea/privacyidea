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

  let mockObserver: { observe: jest.Mock; disconnect: jest.Mock };
  let intersectionCallback: (entries: Partial<IntersectionObserverEntry>[]) => void;
  let originalIntersectionObserver: any;

  beforeEach(async () => {
    originalIntersectionObserver = (global as any).IntersectionObserver;
    mockObserver = { observe: jest.fn(), disconnect: jest.fn() };
    (global as any).IntersectionObserver = jest.fn().mockImplementation((cb: any) => {
      intersectionCallback = cb;
      return mockObserver;
    });

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
    (global as any).IntersectionObserver = originalIntersectionObserver;
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

  describe("sticky header behavior", () => {
    it("observes the sentinel element on init", () => {
      expect(mockObserver.observe).toHaveBeenCalledTimes(1);
    });

    it("passes the provided scroll container as IntersectionObserver root", () => {
      expect((global as any).IntersectionObserver).toHaveBeenCalledWith(
        expect.any(Function),
        { root: scrollEl, threshold: [0, 1] }
      );
    });

    it("adds 'is-sticky' class to the header when sentinel scrolls above the root", () => {
      intersectionCallback([
        {
          boundingClientRect: { top: -10 } as DOMRect,
          rootBounds: { top: 0 } as DOMRect
        }
      ]);

      const header: HTMLElement = fixture.nativeElement.querySelector(".sticky-header");
      expect(header.classList.contains("is-sticky")).toBe(true);
    });

    it("removes 'is-sticky' class when sentinel is back inside the root", () => {
      intersectionCallback([
        { boundingClientRect: { top: -10 } as DOMRect, rootBounds: { top: 0 } as DOMRect }
      ]);
      intersectionCallback([
        { boundingClientRect: { top: 5 } as DOMRect, rootBounds: { top: 0 } as DOMRect }
      ]);

      const header: HTMLElement = fixture.nativeElement.querySelector(".sticky-header");
      expect(header.classList.contains("is-sticky")).toBe(false);
    });

    it("does nothing when rootBounds is null", () => {
      intersectionCallback([{ boundingClientRect: { top: -10 } as DOMRect, rootBounds: null }]);

      const header: HTMLElement = fixture.nativeElement.querySelector(".sticky-header");
      expect(header.classList.contains("is-sticky")).toBe(false);
    });

    it("disconnects the IntersectionObserver on destroy", () => {
      component.ngOnDestroy();
      expect(mockObserver.disconnect).toHaveBeenCalledTimes(1);
    });
  });
});