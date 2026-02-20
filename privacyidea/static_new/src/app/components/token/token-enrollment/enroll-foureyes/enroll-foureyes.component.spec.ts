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

import { EnrollFoureyesComponent } from "./enroll-foureyes.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";

describe("EnrollFoureyesComponent", () => {
  let component: EnrollFoureyesComponent;
  let fixture: ComponentFixture<EnrollFoureyesComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollFoureyesComponent, NoopAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollFoureyesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("ngOnInit with enrollmentData input", () => {
    it("should set initial values from enrollmentData", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "4eyes",
        separator: ":",
        requiredTokenOfRealms: [{ realm: "realm1", tokens: 1 }, { realm: "realm2", tokens: 2 }]
      });
      component.ngOnInit();
      expect(component.separatorControl.value).toBe(":");
      expect(component.requiredTokensOfRealmsControl.value).toEqual(["realm1", "realm2"]);
      expect(component.tokensByRealm).toEqual(new Map([["realm1", 1], ["realm2", 2]]));
    });

    it("should ignore values from enrollmentData if they are undefined", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "4eyes",
        separator: undefined,
        requiredTokenOfRealms: undefined
      });
      component.ngOnInit();
      expect(component.separatorControl.value).toBe("|");
      expect(component.requiredTokensOfRealmsControl.value).toEqual([]);
      expect(component.tokensByRealm).toEqual(new Map());
    });
  });
});
