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
import { EnrollFoureyesComponent } from "./enroll-foureyes.component";
import { RealmService } from "@services/realm/realm.service";
import { MockRealmService, MockTokenService } from "@testing/mock-services";
import { TokenService } from "@services/token/token.service";
import { clearOverlays, flushFixture, matSelectAt } from "@testing/enroll-form-dom";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";

describe("EnrollFoureyesComponent", () => {
  let component: EnrollFoureyesComponent;
  let fixture: ComponentFixture<EnrollFoureyesComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollFoureyesComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: RealmService, useClass: MockRealmService },
        { provide: TokenService, useClass: MockTokenService }
      ]
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
        requiredTokenOfRealms: [
          { realm: "realm1", tokens: 1 },
          { realm: "realm2", tokens: 2 }
        ]
      });
      fixture.detectChanges();
      expect(component.separator()).toBe(":");
      expect(component.requiredTokensOfRealms()).toEqual(["realm1", "realm2"]);
      expect(component.tokensByRealm).toEqual(
        new Map([
          ["realm1", 1],
          ["realm2", 2]
        ])
      );
    });

    it("should ignore values from enrollmentData if they are undefined", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "4eyes",
        separator: undefined,
        requiredTokenOfRealms: undefined
      });
      fixture.detectChanges();
      expect(component.separator()).toBe("|");
      expect(component.requiredTokensOfRealms()).toEqual([]);
      expect(component.tokensByRealm).toEqual(new Map());
    });
  });

  describe("bound controls", () => {
    afterEach(clearOverlays);

    beforeEach(async () => {
      (TestBed.inject(RealmService) as unknown as MockRealmService).realmOptions.set(["realm1", "realm2"]);
      await flushFixture(fixture);
    });

    it("writes the picked realms to the model and marks the field dirty", async () => {
      const select = matSelectAt(fixture);
      select.open();
      await flushFixture(fixture);
      (select.panel.nativeElement.querySelectorAll("mat-option")[1] as HTMLElement).click();
      await flushFixture(fixture);

      expect(component.requiredTokensOfRealms()).toEqual(["realm2"]);
      expect(component.requiredTokensOfRealmsForm().dirty()).toBe(true);
    });

    it("refuses the build without a realm and renders the required error", async () => {
      expect(component.buildEnrollmentArgs({ type: "4eyes" } as TokenEnrollmentData)).toBeNull();
      await flushFixture(fixture);

      expect(component.requiredTokensOfRealmsForm().touched()).toBe(true);
      expect(fixture.nativeElement.textContent).toContain("At least one realm is required");
    });

    it("builds the arguments once a realm is selected", () => {
      component.requiredTokensOfRealms.set(["realm1"]);

      expect(component.buildEnrollmentArgs({ type: "4eyes" } as TokenEnrollmentData)).not.toBeNull();
    });

    it("requires one token of a realm that has no count of its own", () => {
      component.requiredTokensOfRealms.set(["realm1", "realm2"]);
      component.setTokenCount("realm2", 3);

      const args = component.buildEnrollmentArgs({ type: "4eyes" } as TokenEnrollmentData);

      expect(args?.data).toEqual(
        expect.objectContaining({
          requiredTokenOfRealms: [
            { realm: "realm1", tokens: 1 },
            { realm: "realm2", tokens: 3 }
          ]
        })
      );
    });
  });
});
