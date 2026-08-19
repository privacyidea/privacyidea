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
import { DetailsListDisplayComponent } from "./details-list-display.component";

describe("DetailsListDisplayComponent", () => {
  let fixture: ComponentFixture<DetailsListDisplayComponent>;
  let component: DetailsListDisplayComponent;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [DetailsListDisplayComponent] });
    fixture = TestBed.createComponent(DetailsListDisplayComponent);
    component = fixture.componentInstance;
  });

  it("renders one list item per entry", () => {
    fixture.componentRef.setInput("items", ["realm1", "realm2"]);
    fixture.detectChanges();

    const el: HTMLElement = fixture.nativeElement;
    const items = el.querySelectorAll("mat-list-item");
    expect(items.length).toBe(2);
    expect(items[0].textContent).toContain("realm1");
    expect(items[1].textContent).toContain("realm2");
  });

  it("renders nothing for an empty list", () => {
    fixture.componentRef.setInput("items", []);
    fixture.detectChanges();

    expect(component).toBeTruthy();
    expect(fixture.nativeElement.querySelectorAll("mat-list-item").length).toBe(0);
  });
});
