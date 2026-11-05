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
import { NO_REALM_SENTINEL, parseRealms, RealmSelectComponent, realmParam } from "./realm-select.component";

describe("realm helpers", () => {
  it("parseRealms trims the entries and drops empty ones", () => {
    expect(parseRealms(" a, b ,,c")).toEqual(["a", "b", "c"]);
    expect(parseRealms("")).toEqual([]);
    expect(parseRealms(undefined)).toEqual([]);
  });

  it("realmParam drops the empty selection and the no-realm sentinel", () => {
    expect(realmParam("")).toBeUndefined();
    expect(realmParam(NO_REALM_SENTINEL)).toBeUndefined();
    expect(realmParam("realm1")).toBe("realm1");
  });
});

describe("RealmSelectComponent", () => {
  let fixture: ComponentFixture<RealmSelectComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [RealmSelectComponent] });
    fixture = TestBed.createComponent(RealmSelectComponent);
    fixture.componentRef.setInput("realms", ["realm1", "realm2"]);
    fixture.componentRef.setInput("realm", "realm1");
    fixture.detectChanges();
  });

  it("lists the realms", () => {
    fixture.debugElement.query(By.css("mat-select")).componentInstance.open();
    fixture.detectChanges();
    const options = document.querySelectorAll("mat-option");
    expect(options.length).toBe(2);
    expect(options[1].textContent).toContain("realm2");
  });

  it("clears the selection with the clear button", () => {
    const event = new MouseEvent("click");
    const stop = jest.spyOn(event, "stopPropagation");
    fixture.componentInstance.clearRealmSelection(event);
    expect(stop).toHaveBeenCalled();
    expect(fixture.componentInstance.realm()).toBe("");
  });
});
