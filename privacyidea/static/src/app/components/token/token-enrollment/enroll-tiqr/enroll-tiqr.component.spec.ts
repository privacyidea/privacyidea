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

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { provideRouter } from "@angular/router";
import { EnrollTiqrComponent } from "./enroll-tiqr.component";
import { AuthService } from "@services/auth/auth.service";
import { SystemService } from "@services/system/system.service";
import { MockAuthService, MockSystemService, MockTokenService } from "@testing/mock-services";
import { TokenService } from "@services/token/token.service";

describe("EnrollTiqrComponent", () => {
  let component: EnrollTiqrComponent;
  let fixture: ComponentFixture<EnrollTiqrComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollTiqrComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: AuthService, useClass: MockAuthService },
        { provide: SystemService, useClass: MockSystemService },
        { provide: TokenService, useClass: MockTokenService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollTiqrComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("missing TiQR configuration", () => {
    const warning = (): HTMLElement => fixture.nativeElement.querySelector(".inline-warning");

    const setRights = (rights: string[]) => {
      const authService = TestBed.inject(AuthService) as unknown as MockAuthService;
      authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights });
      fixture.detectChanges();
    };

    it("links to the token type configuration with the right to read the configuration", () => {
      setRights(["configread"]);

      expect(warning().querySelector("a")?.getAttribute("href")).toBe("/configuration/tokens");
    });

    it("asks to contact the administrator, without a link, without the right to read the configuration", () => {
      setRights([]);

      expect(warning().querySelector("a")).toBeNull();
      expect(warning().textContent).toContain("Please contact your administrator.");
    });
  });
});
