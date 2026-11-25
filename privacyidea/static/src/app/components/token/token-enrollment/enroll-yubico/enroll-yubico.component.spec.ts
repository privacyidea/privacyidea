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
import { EnrollYubicoComponent } from "./enroll-yubico.component";
import { SystemService } from "@services/system/system.service";
import { MockContentService, MockSystemService, MockTokenService } from "@testing/mock-services";
import { TokenService } from "@services/token/token.service";
import { ContentService } from "@services/content/content.service";
import { axe } from "@testing/axe";
import { flushFixture, typeInto } from "@testing/enroll-form-dom";

describe("EnrollYubicoComponent", () => {
  let component: EnrollYubicoComponent;
  let fixture: ComponentFixture<EnrollYubicoComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollYubicoComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: SystemService, useClass: MockSystemService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollYubicoComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("identifier errors", () => {
    const identifierInput = () => fixture.nativeElement.querySelector("input[matInput]") as HTMLInputElement;
    const blurIdentifier = async () => {
      identifierInput().dispatchEvent(new Event("blur"));
      await flushFixture(fixture);
    };

    it("renders only the required error for an empty identifier once the field was touched", async () => {
      await blurIdentifier();

      expect(fixture.nativeElement.textContent).toContain("Yubikey identifier is required");
      expect(fixture.nativeElement.textContent).not.toContain("exactly 12 characters");
    });

    it.each([
      ["shorter", "cccccccccc"],
      ["longer", "ccccccccccccc"]
    ])("renders only the length error for an identifier %s than 12 characters", async (_, value) => {
      await typeInto(fixture, identifierInput(), value);
      await blurIdentifier();

      expect(fixture.nativeElement.textContent).toContain("Yubikey identifier must be exactly 12 characters long.");
      expect(fixture.nativeElement.textContent).not.toContain("Yubikey identifier is required");
    });

    it("accepts an identifier of exactly 12 characters", async () => {
      await typeInto(fixture, identifierInput(), "cccccccccccc");

      expect(component.yubicoIdentifierForm().valid()).toBe(true);
    });
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
