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

import { EnrollSmsComponent } from "./enroll-sms.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";

describe("EnrollSmsComponent", () => {
  let component: EnrollSmsComponent;
  let fixture: ComponentFixture<EnrollSmsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollSmsComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollSmsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("ngOnInit with enrollmentData input", () => {
    it("should set initial values from enrollmentData", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "sms",
        smsGateway: "TestGateway",
        readNumberDynamically: true,
        phoneNumber: "+1234567890"
      });
      fixture.detectChanges();
      component.ngOnInit();
      expect(component.smsGatewayControl.value).toBe("TestGateway");
      expect(component.readNumberDynamicallyControl.value).toBe(true);
      expect(component.phoneNumberControl.value).toBe("+1234567890");
    });

    it("should ignore values from enrollmentData if they are undefined", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "sms",
        smsGateway: undefined,
        readNumberDynamically: undefined,
        phoneNumber: undefined
      });
      component.ngOnInit();
      expect(component.smsGatewayControl.value).toBe("");
      expect(component.readNumberDynamicallyControl.value).toBe(false);
      expect(component.phoneNumberControl.value).toBe("");
    });
  });
});
