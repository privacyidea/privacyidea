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
import { SystemService } from "@services/system/system.service";
import { TokenService } from "@services/token/token.service";
import { MockSystemService, MockTokenService, MockContentService } from "@testing/mock-services";
import { EnrollRadiusComponent } from "./enroll-radius.component";
import { ContentService } from "@services/content/content.service";
import { clearOverlays, clickCheckbox, flushFixture, matSelectAt, pickOption } from "@testing/enroll-form-dom";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";

describe("EnrollRadiusComponent", () => {
  let component: EnrollRadiusComponent;
  let fixture: ComponentFixture<EnrollRadiusComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollRadiusComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: SystemService, useClass: MockSystemService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollRadiusComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("bound controls", () => {
    afterEach(clearOverlays);

    it("writes a click on the checkbox to the model and marks the field dirty", async () => {
      expect(component.checkPinLocallyForm().dirty()).toBe(false);

      await clickCheckbox(fixture);

      expect(component.checkPinLocally()).toBe(true);
      expect(component.checkPinLocallyForm().dirty()).toBe(true);
    });

    it("writes the picked RADIUS server to the model", async () => {
      (TestBed.inject(SystemService) as unknown as MockSystemService).radiusServers.set(["radius-a", "radius-b"]);
      await flushFixture(fixture);

      await pickOption(fixture, matSelectAt(fixture), 1);

      expect(component.radiusServerConfiguration()).toBe("radius-b");
      expect(component.radiusServerConfigurationForm().dirty()).toBe(true);
    });

    it("renders the required error of the server select once the build was refused", async () => {
      expect(fixture.nativeElement.querySelector("mat-error")).toBeNull();

      expect(component.buildEnrollmentArgs({ type: "radius" } as TokenEnrollmentData)).toBeNull();
      await flushFixture(fixture);

      expect(fixture.nativeElement.textContent).toContain("RADIUS Server is required");
    });
  });
});
