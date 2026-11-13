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
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { DetailsEditRegistry } from "@components/shared/details-shared/field-editing/details-edit-registry.service";
import { AuthService } from "@services/auth/auth.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { TokenService } from "@services/token/token.service";
import { MockTableUtilsService, MockTokenService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { mockTokenDetails } from "@testing/mock-token-details";
import { TokenDetailsStatusComponent } from "./token-details-status.component";
import { axe } from "@testing/axe";

describe("TokenDetailsStatusComponent", () => {
  let component: TokenDetailsStatusComponent;
  let fixture: ComponentFixture<TokenDetailsStatusComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenDetailsStatusComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        DetailsEditRegistry,
        { provide: TokenService, useClass: MockTokenService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: TableUtilsService, useClass: MockTableUtilsService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenDetailsStatusComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("tokenDetails", mockTokenDetails());
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("renders the inline status row by default and an extra detail field in self-service mode", () => {
    // admin: Type + Rollout State are detail fields; Status is the inline toggle row
    expect(fixture.nativeElement.querySelectorAll("app-detail-field").length).toBe(2);

    fixture.componentRef.setInput("selfService", true);
    fixture.detectChanges();
    // self-service: Status becomes a detail field as well
    expect(fixture.nativeElement.querySelectorAll("app-detail-field").length).toBe(3);
  });

  describe("status toggle", () => {
    const toggle = (): HTMLButtonElement => fixture.nativeElement.querySelector("button.status-toggle");
    const description = (): string | undefined =>
      toggle()
        .getAttribute("aria-describedby")
        ?.split(" ")
        .map((id) => document.getElementById(id)?.textContent?.trim())
        .join(" ");

    beforeEach(() => {
      (TestBed.inject(AuthService) as unknown as MockAuthService).authData.set({
        ...MockAuthService.MOCK_AUTH_DATA,
        rights: ["enable", "disable"]
      });
      fixture.detectChanges();
    });

    it("is named by the state it shows", () => {
      expect(toggle().hasAttribute("aria-label")).toBe(false);
      expect(toggle().textContent?.trim()).toBe("Active");
    });

    it("passes the axe accessibility checks", async () => {
      expect(await axe(fixture.nativeElement)).toHaveNoViolations();
    });

    it("describes what pressing it does with the tooltip of the token tables", () => {
      const tableUtils = TestBed.inject(TableUtilsService) as unknown as MockTableUtilsService;
      tableUtils.getTooltipForColumn.mockImplementation((_: string, row: { active: boolean }) =>
        row.active ? "Deactivate Token" : "Activate Token"
      );
      (TestBed.inject(TokenService) as unknown as MockTokenService).tokenIsActive.set(false);
      fixture.detectChanges();
      expect(description()).toBe("Activate Token");

      (TestBed.inject(TokenService) as unknown as MockTokenService).tokenIsActive.set(true);
      fixture.detectChanges();

      expect(description()).toBe("Deactivate Token");
      expect(tableUtils.getTooltipForColumn).toHaveBeenCalledWith("active", { active: true });
    });
  });
});
