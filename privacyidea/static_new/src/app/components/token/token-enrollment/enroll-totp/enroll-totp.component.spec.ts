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

import { EnrollTotpComponent } from "./enroll-totp.component";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

describe("EnrollTotpComponent", () => {
  let component: EnrollTotpComponent;
  let fixture: ComponentFixture<EnrollTotpComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollTotpComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("ngOnInit with enrollmentData input", () => {
    it("should set initial values from enrollmentData", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "totp",
        generateOnServer: false,
        otpLength: 8,
        hashAlgorithm: "sha512",
        timeStep: 45
      });
      component.ngOnInit();
      expect(component.generateOnServerFormControl.value).toBe(false);
      expect(component.otpLengthFormControl.value).toBe(8);
      expect(component.hashAlgorithmControl.value).toBe("sha512");
    });

    it("should ignore values from enrollmentData if they are undefined", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "totp",
        generateOnServer: undefined,
        otpLength: undefined,
        hashAlgorithm: undefined,
        timeStep: undefined
      });
      component.ngOnInit();
      expect(component.generateOnServerFormControl.value).toBe(true);
      expect(component.otpLengthFormControl.value).toBe(6);
      expect(component.hashAlgorithmControl.value).toBe("sha1");
    });
  });
});
