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
import { BreakableCodeComponent } from "./breakable-code.component";

describe("BreakableCodeComponent", () => {
  let fixture: ComponentFixture<BreakableCodeComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [BreakableCodeComponent] }).compileComponents();
    fixture = TestBed.createComponent(BreakableCodeComponent);
  });

  function render(text: string | null): HTMLElement {
    fixture.componentRef.setInput("text", text);
    fixture.detectChanges();
    return fixture.nativeElement;
  }

  it("offers a break after each underscore", () => {
    const host = render("WEBUI_PASSKEY_LOGIN_DISABLED");

    expect(host.innerHTML.replace(/<!--.*?-->/g, "")).toBe(
      "<span>WEBUI_</span><wbr><span>PASSKEY_</span><wbr><span>LOGIN_</span><wbr><span>DISABLED</span>"
    );
  });

  it("keeps the text exactly as given", () => {
    expect(render("AUTH_MAX_FAIL").textContent).toBe("AUTH_MAX_FAIL");
  });

  it("renders a value without an underscore as one segment", () => {
    expect(render("SUCCESS").querySelectorAll("wbr").length).toBe(0);
  });

  it("renders nothing for a missing value", () => {
    expect(render(null).textContent).toBe("");
  });
});
