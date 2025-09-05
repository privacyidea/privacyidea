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
import { TokenDetailsActionsComponent } from "./token-details-actions.component";
import { TokenService } from "../../../../services/token/token.service";
import { ValidateService } from "../../../../services/validate/validate.service";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { signal } from "@angular/core";
import { MockTokenService } from "../../../../../testing/mock-services";

describe("TokenDetailsActionsComponent", () => {
  let component: TokenDetailsActionsComponent;
  let fixture: ComponentFixture<TokenDetailsActionsComponent>;

  beforeEach(async () => {
    jest.clearAllMocks();
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TokenDetailsActionsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        ValidateService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenDetailsActionsComponent);
    component = fixture.componentInstance;
    component.tokenSerial = signal("Mock serial");
    component.tokenType = signal("Mock type");

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
