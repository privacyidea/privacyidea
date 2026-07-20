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
});
