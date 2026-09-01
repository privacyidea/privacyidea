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

import { InfoCell } from "./info-cell";

describe("InfoCell", () => {
  let component: InfoCell;
  let fixture: ComponentFixture<InfoCell>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [InfoCell] }).compileComponents();
    fixture = TestBed.createComponent(InfoCell);
    component = fixture.componentInstance;
  });

  function entriesFor(info: unknown) {
    fixture.componentRef.setInput("info", info);
    return component.entries();
  }

  it("renders key/value rows, a sub-list for one level of nesting and JSON for deeper nesting", () => {
    expect(entriesFor(null)).toEqual([]);
    expect(
      entriesFor({
        serial: "TOTP001",
        roles: ["admin", "user"],
        truncated: { username: "abc", deep: { x: 1 } },
        n: 3
      })
    ).toEqual([
      { key: "Serial", value: "TOTP001" },
      {
        key: "Roles",
        children: [
          { key: "", value: "admin" },
          { key: "", value: "user" }
        ]
      },
      {
        key: "Truncated",
        children: [
          { key: "Username", value: "abc" },
          { key: "Deep", value: '{"x":1}' }
        ]
      },
      { key: "N", value: "3" }
    ]);
  });

  it("humanizes snake_case keys and uppercases the acronyms that actually occur", () => {
    // The keys are the truncated authentication-log columns, which is all other_info can hold today.
    expect(entriesFor({ client_label: "vpn", source_ip: "1.2.3.4", transaction_id: "0576", uid: "1000" })).toEqual([
      { key: "Client label", value: "vpn" },
      { key: "Source IP", value: "1.2.3.4" },
      { key: "Transaction ID", value: "0576" },
      { key: "UID", value: "1000" }
    ]);
  });

  it("leaves a fragment it does not know as a word rather than guessing at an acronym", () => {
    expect(entriesFor({ webauthn_aaguid: "d8522d9f", otp_pin: "1234" })).toEqual([
      { key: "Webauthn aaguid", value: "d8522d9f" },
      { key: "Otp pin", value: "1234" }
    ]);
  });

  it("gives a list one bullet per element, and folds an element's own nesting into JSON", () => {
    // A list nests one level like a dict, but its elements have no key of their own (only the bullet marks them), so a
    // dict element folds to JSON instead of being rendered further.
    expect(entriesFor({ items: [{ a: 1 }, { a: 2 }] })).toEqual([
      {
        key: "Items",
        children: [
          { key: "", value: '{"a":1}' },
          { key: "", value: '{"a":2}' }
        ]
      }
    ]);
  });

  it("renders an empty list like an empty dict: the key, with nothing under it", () => {
    expect(entriesFor({ tags: [], detail: {} })).toEqual([
      { key: "Tags", children: [] },
      { key: "Detail", children: [] }
    ]);
  });

  it("renders nothing for a value that is not a dict", () => {
    // The table's skeleton rows set every column to "" (neither null nor a dict), so a cell that walks JSON must not
    // throw on that value.
    expect(entriesFor("")).toEqual([]);
    expect(entriesFor(["a", "b"])).toEqual([]);
    expect(entriesFor(undefined)).toEqual([]);
  });

  it("shows a list in the DOM as bullets under its key", () => {
    // This also verifies the sub-list is not tracked by key: list elements have no key, so two of them would collide if
    // it were.
    fixture.componentRef.setInput("info", { policies_applied: ["otppin=userstore", "challenge_response=hotp"] });
    fixture.detectChanges();

    const bullets: HTMLLIElement[] = Array.from(fixture.nativeElement.querySelectorAll(".info-sublist li"));
    expect(bullets.map((bullet) => bullet.textContent?.trim())).toEqual([
      "otppin=userstore",
      "challenge_response=hotp"
    ]);
    expect(fixture.nativeElement.querySelector(".info-group .info-key").textContent).toBe("Policies applied");
  });
});
