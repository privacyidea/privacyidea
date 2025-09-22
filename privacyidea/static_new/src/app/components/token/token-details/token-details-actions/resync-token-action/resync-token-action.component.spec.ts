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

import { ResyncTokenActionComponent } from "./resync-token-action.component";
import { TokenService } from "../../../../../services/token/token.service";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MockTokenService } from "../../../../../../testing/mock-services";


describe("ResyncTokenActionComponent", () => {
  let component: ResyncTokenActionComponent;
  let fixture: ComponentFixture<ResyncTokenActionComponent>;
  let tokenService: TokenService;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [ResyncTokenActionComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService }
      ]
    })
      .compileComponents();

    tokenService = TestBed.inject(TokenService);
    tokenService.tokenSerial.set("Mock serial");
    fixture = TestBed.createComponent(ResyncTokenActionComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should resync OTP token", () => {
    component.fristOTPValue = "otp1";
    component.secondOTPValue = "otp2";

    const resyncSpy = jest.spyOn(tokenService, "resyncOTPToken");
    component.resyncOTPToken();

    expect(resyncSpy).toHaveBeenCalledWith("Mock serial", "otp1", "otp2");
  });

  it("should resync OTP token on button click", () => {
    component.fristOTPValue = "otp1";
    component.secondOTPValue = "otp2";

    const resyncSpy = jest.spyOn(tokenService, "resyncOTPToken");

    const btn: HTMLButtonElement = fixture.nativeElement.querySelector(
      ".actions-pin-input-button button"
    );
    btn.click();

    expect(resyncSpy).toHaveBeenCalledWith("Mock serial", "otp1", "otp2");
  });
});
