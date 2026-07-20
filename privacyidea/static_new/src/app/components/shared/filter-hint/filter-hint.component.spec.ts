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
import { FilterHintComponent } from "./filter-hint.component";

describe("FilterHintComponent", () => {
  let component: FilterHintComponent;
  let fixture: ComponentFixture<FilterHintComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FilterHintComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(FilterHintComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("mentions the keyword syntax and the wildcard by default", () => {
    expect(component.hintText()).toContain("keyword: value");
    expect(component.hintText()).toContain("*");
    expect(component.hintText()).toContain("case-insensitive");
  });

  it("omits the keyword syntax when keywords are not supported", () => {
    fixture.componentRef.setInput("supportsKeywords", false);
    fixture.detectChanges();

    expect(component.hintText()).not.toContain("keyword: value");
  });

  it("reports case-sensitive matching when configured", () => {
    fixture.componentRef.setInput("caseSensitive", true);
    fixture.detectChanges();

    expect(component.hintText()).toContain("case-sensitive");
    expect(component.hintText()).not.toContain("usually case-insensitive");
  });

  it("lists the example and available keywords", () => {
    fixture.componentRef.setInput("example", "type: hotp");
    fixture.componentRef.setInput("keywords", ["serial", "type"]);
    fixture.detectChanges();

    const hint = component.hintText();
    expect(hint).toContain("type: hotp");
    expect(hint).toContain("serial, type");
  });
});
