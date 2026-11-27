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
import { EnrollmentPolicyErrorComponent } from "./enrollment-policy-error.component";

describe("EnrollmentPolicyErrorComponent", () => {
  let fixture: ComponentFixture<EnrollmentPolicyErrorComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [EnrollmentPolicyErrorComponent] }).compileComponents();
    fixture = TestBed.createComponent(EnrollmentPolicyErrorComponent);
  });

  it("renders nothing without an error", () => {
    fixture.componentRef.setInput("error", null);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("p")).toBeNull();
  });

  it("renders the error as an alert", () => {
    fixture.componentRef.setInput("error", "The enrollment policies could not be determined.");
    fixture.detectChanges();

    const paragraph: HTMLElement = fixture.nativeElement.querySelector("p.inline-warning");
    expect(paragraph.getAttribute("role")).toBe("alert");
    expect(paragraph.textContent).toContain("The enrollment policies could not be determined.");
  });
});
