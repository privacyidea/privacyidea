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

  it("assignUserToToken: calls service, navigates to details, and updates tokenSerial", () => {
    const serial = "TKN-123";
    const pin = "1234";

    component.selectedToken.set(serial);
    component.setPinValue.set(pin);

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
});
