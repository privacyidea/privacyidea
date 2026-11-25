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
import { EnrollVascoComponent } from "./enroll-vasco.component";
import { TokenService } from "@services/token/token.service";
import { MockTokenService } from "@testing/mock-services";
import { clickCheckbox, flushFixture, typeInto } from "@testing/enroll-form-dom";
import { axe } from "@testing/axe";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { VascoEnrollmentData } from "@app/mappers/token-api-payload/vasco-token-api-payload.mapper";

// A blob whose first ten characters, hex-decoded, are the VASCO serial "VAS1234567".
const BLOB = Array.from("VAS1234567", (char) => char.charCodeAt(0).toString(16))
  .join("")
  .padEnd(496, "0");

describe("EnrollVascoComponent", () => {
  let component: EnrollVascoComponent;
  let fixture: ComponentFixture<EnrollVascoComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollVascoComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollVascoComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  const blobInput = () => fixture.nativeElement.querySelector("textarea") as HTMLTextAreaElement;
  const serialInLabel = () => fixture.nativeElement.querySelector("mat-checkbox code") as HTMLElement | null;
  const build = () => component.buildEnrollmentArgs({ type: "vasco" } as TokenEnrollmentData);

  it("shows the serial read from the blob in the checkbox label", async () => {
    expect(serialInLabel()).toBeNull();

    await typeInto(fixture, blobInput(), BLOB);

    expect(serialInLabel()?.textContent).toBe("VAS1234567");
  });

  it("shows no serial for a blob of the right length with characters that are not hex", async () => {
    await typeInto(fixture, blobInput(), BLOB.slice(1) + "g");

    expect(serialInLabel()).toBeNull();
  });

  it("writes a click on the checkbox to the model and keeps the blob enabled", async () => {
    await clickCheckbox(fixture);

    expect(component.useVascoSerial()).toBe(true);
    expect(component.useVascoSerialForm().dirty()).toBe(true);
    expect(component.otpKeyForm().disabled()).toBe(false);
  });

  it("sends the blob and the serial read from it when the checkbox is set", async () => {
    await typeInto(fixture, blobInput(), BLOB);
    await clickCheckbox(fixture);

    const data = build()!.data as VascoEnrollmentData;
    expect(data.otpKey).toBe(BLOB);
    expect(data.vascoSerial).toBe("VAS1234567");
  });

  it("sends only the blob when the checkbox is not set", async () => {
    await typeInto(fixture, blobInput(), BLOB);

    const data = build()!.data as VascoEnrollmentData;
    expect(data.otpKey).toBe(BLOB);
    expect(data.vascoSerial).toBeUndefined();
  });

  it("renders only the required error for an empty blob on enrollment", async () => {
    expect(build()).toBeNull();
    await flushFixture(fixture);

    expect(fixture.nativeElement.textContent).toContain("VASCO Token blob is required");
    expect(fixture.nativeElement.textContent).not.toContain("496-character hex string");
  });

  it.each([
    ["too short", BLOB.slice(1)],
    ["not hex", BLOB.slice(1) + "g"]
  ])("renders only the format error for a blob that is %s on enrollment", async (_, blob) => {
    await typeInto(fixture, blobInput(), blob);
    expect(build()).toBeNull();
    await flushFixture(fixture);

    expect(fixture.nativeElement.textContent).toContain("496-character hex string");
    expect(fixture.nativeElement.textContent).not.toContain("VASCO Token blob is required");
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
