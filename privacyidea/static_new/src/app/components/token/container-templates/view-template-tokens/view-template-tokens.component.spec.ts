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
import { ViewTemplateTokensComponent } from "./view-template-tokens.component";
import { By } from "@angular/platform-browser";

describe("ViewTemplateTokensComponent", () => {
  let component: ViewTemplateTokensComponent;
  let fixture: ComponentFixture<ViewTemplateTokensComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ViewTemplateTokensComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(ViewTemplateTokensComponent);
    component = fixture.componentInstance;
  });

  it("should create", () => {
    fixture.componentRef.setInput("templateTokens", []);
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it("should display tokens correctly", () => {
    const mockTokens = [
      { type: "TOTP", serial: "12345" },
      { type: "WebAuthn", description: "Yubikey" }
    ];

    fixture.componentRef.setInput("templateTokens", mockTokens);
    fixture.detectChanges();
    TestBed.tick();

    const tokenContainers = fixture.debugElement.queryAll(By.css(".token-container"));
    expect(tokenContainers.length).toBe(2);

    const firstTokenText = tokenContainers[0].nativeElement.textContent.replace(/\s+/g, " ").trim();
    expect(firstTokenText).toContain("Type: TOTP");
    expect(firstTokenText).toContain("serial: 12345");
  });

  it("should not render container if tokens are empty", () => {
    fixture.componentRef.setInput("templateTokens", []);
    fixture.detectChanges();
    TestBed.tick();

    const container = fixture.debugElement.query(By.css(".template-tokens-container"));
    expect(container).toBeNull();
  });

  it("should exclude type from keyvalue loop to avoid duplication", () => {
    const mockTokens = [{ type: "HOTP", counter: "1" }];

    fixture.componentRef.setInput("templateTokens", mockTokens);
    fixture.detectChanges();
    TestBed.tick();

    const items = fixture.debugElement.queryAll(By.css(".token-item"));
    const labels = items.map((i) => i.nativeElement.textContent);

    const typeOccurrences = labels.filter((l) => l.includes("Type:"));
    expect(typeOccurrences.length).toBe(1);
  });
});
