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
import { By } from "@angular/platform-browser";
import { CopyButtonComponent } from "@components/shared/copy-button/copy-button.component";
import { axe } from "@testing/axe";
import { EnrollmentSecretComponent } from "./enrollment-secret.component";

describe("EnrollmentSecretComponent", () => {
  const SECRET = "s3cr3t-value";
  let fixture: ComponentFixture<EnrollmentSecretComponent>;
  let saved: number;

  const toggle = () => fixture.nativeElement.querySelector(".enrollment-secret__toggle") as HTMLButtonElement;
  const shownValue = () => (fixture.nativeElement.querySelector("code") as HTMLElement).textContent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [EnrollmentSecretComponent] }).compileComponents();
    fixture = TestBed.createComponent(EnrollmentSecretComponent);
    fixture.componentRef.setInput("label", "Registration Code");
    fixture.componentRef.setInput("value", SECRET);
    saved = 0;
    fixture.componentInstance.saved.subscribe(() => saved++);
    fixture.detectChanges();
  });

  it("masks the secret until it is revealed", () => {
    expect(shownValue()).toBe("•".repeat(SECRET.length));
    expect(toggle().getAttribute("aria-label")).toBe("Show Registration Code");

    toggle().click();
    fixture.detectChanges();

    expect(shownValue()).toBe(SECRET);
    expect(toggle().getAttribute("aria-label")).toBe("Hide Registration Code");
  });

  it("gives screen readers a word instead of the mask", () => {
    const code = () => fixture.nativeElement.querySelector("code") as HTMLElement;
    const hiddenText = () => fixture.nativeElement.querySelector(".visually-hidden") as HTMLElement | null;

    expect(code().getAttribute("aria-hidden")).toBe("true");
    expect(hiddenText()?.textContent).toBe("hidden");

    toggle().click();
    fixture.detectChanges();

    expect(code().hasAttribute("aria-hidden")).toBe(false);
    expect(hiddenText()).toBeNull();
  });

  it("counts revealing as saved, hiding again does not", () => {
    toggle().click();
    toggle().click();

    expect(saved).toBe(1);
  });

  it("copies the secret while it is masked and counts that as saved", () => {
    const copyButton = fixture.debugElement.query(By.directive(CopyButtonComponent))
      .componentInstance as CopyButtonComponent;

    expect(copyButton.copyText()).toBe(SECRET);
    copyButton.onCopy();

    expect(saved).toBe(1);
    expect(shownValue()).toBe("•".repeat(SECRET.length));
  });

  it("shows the hint only when one is given", () => {
    expect(fixture.nativeElement.querySelector("p")).toBeNull();

    fixture.componentRef.setInput("hint", "Save it now.");
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("p").textContent).toBe("Save it now.");
  });

  it("passes the axe accessibility checks", async () => {
    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
