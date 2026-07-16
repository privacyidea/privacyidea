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
import { TokenService } from "@services/token/token.service";
import { MockTokenService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { mockTokenDetails } from "@testing/mock-token-details";
import { TokenDetailsCountersComponent } from "./token-details-counters.component";

describe("TokenDetailsCountersComponent", () => {
  let component: TokenDetailsCountersComponent;
  let fixture: ComponentFixture<TokenDetailsCountersComponent>;
  let tokenSvc: MockTokenService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenDetailsCountersComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        DetailsEditRegistry,
        { provide: TokenService, useClass: MockTokenService },
        { provide: AuthService, useClass: MockAuthService }
      ]
    }).compileComponents();

    tokenSvc = TestBed.inject(TokenService) as unknown as MockTokenService;

    fixture = TestBed.createComponent(TokenDetailsCountersComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("tokenDetails", mockTokenDetails());
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("saveMaxfail persists the value and reloads", () => {
    tokenSvc.tokenSerial.set("Mock serial");
    const reloadSpy = tokenSvc.tokenDetailResource.reload as jest.Mock;
    reloadSpy.mockClear();

    component["saveMaxfail"]("15");

    expect(tokenSvc.saveTokenDetail).toHaveBeenCalledWith("Mock serial", "maxfail", "15");
    expect(reloadSpy).toHaveBeenCalled();
  });
});
