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
import { InfoHintComponent } from "./info-hint.component";

describe("InfoHintComponent", () => {
  let component: InfoHintComponent;
  let fixture: ComponentFixture<InfoHintComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [InfoHintComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(InfoHintComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("text", "Explanation here.");
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should render the info icon", () => {
    const icon = fixture.debugElement.query(By.css("mat-icon"));
    expect(icon.nativeElement.textContent).toContain("info_outline");
  });

  it("should default the aria-label and allow overriding it", () => {
    let button = fixture.debugElement.query(By.css("button"));
    expect(button.nativeElement.getAttribute("aria-label")).toBe("More information");

    fixture.componentRef.setInput("ariaLabel", "About priority");
    fixture.detectChanges();
    button = fixture.debugElement.query(By.css("button"));
    expect(button.nativeElement.getAttribute("aria-label")).toBe("About priority");
  });
});
