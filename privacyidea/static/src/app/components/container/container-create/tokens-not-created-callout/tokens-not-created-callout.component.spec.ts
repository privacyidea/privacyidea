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
import { ContainerTokenNotCreated } from "@services/container/container.service";
import { TokensNotCreatedCalloutComponent } from "./tokens-not-created-callout.component";

describe("TokensNotCreatedCalloutComponent", () => {
  let fixture: ComponentFixture<TokensNotCreatedCalloutComponent>;

  const notCreated: ContainerTokenNotCreated[] = [
    { type: "hotp", error: "Policy hotp_blocked forbids it", serial: "OATH0009" },
    { type: "totp", error: "Maximum number of tokens reached" }
  ];

  const render = (tokensNotCreated: ContainerTokenNotCreated[] | undefined, allFailed?: boolean) => {
    fixture.componentRef.setInput("tokensNotCreated", tokensNotCreated);
    if (allFailed !== undefined) {
      fixture.componentRef.setInput("allFailed", allFailed);
    }
    fixture.detectChanges();
  };
  const callout = () => fixture.nativeElement.querySelector('[data-testid="tokens-not-created"]') as HTMLElement | null;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [TokensNotCreatedCalloutComponent] }).compileComponents();
    fixture = TestBed.createComponent(TokensNotCreatedCalloutComponent);
  });

  it("renders nothing by default", () => {
    fixture.detectChanges();

    expect(callout()).toBeNull();
  });

  it.each([[undefined], [[]]])("renders nothing when tokensNotCreated is %j", (value) => {
    render(value as ContainerTokenNotCreated[] | undefined);

    expect(callout()).toBeNull();
    expect(fixture.nativeElement.textContent.trim()).toBe("");
  });

  it("lists every token as '<type> (<error>)' in a red callout", () => {
    render(notCreated);

    const items = Array.from(callout()!.querySelectorAll("li")).map((li) => (li as HTMLElement).textContent!.trim());
    expect(items).toEqual(["hotp (Policy hotp_blocked forbids it)", "totp (Maximum number of tokens reached)"]);
    expect(callout()!.classList).toContain("inline-callout");
    expect(callout()!.classList).toContain("inline-callout-error");
  });

  it("uses the singular heading for one token", () => {
    render([notCreated[0]]);

    expect(callout()!.textContent).toContain("This token of the template was not created:");
    expect(callout()!.textContent).not.toContain("These tokens");
    expect(callout()!.querySelector(".error-message")).toBeNull();
  });

  it("uses the plural heading for several tokens", () => {
    render(notCreated);

    expect(callout()!.textContent).toContain("These tokens of the template were not created:");
    expect(callout()!.querySelector(".error-message")).toBeNull();
  });

  it("shows only the 'none created' error heading when all tokens failed", () => {
    render(notCreated, true);

    const error = callout()!.querySelector(".error-message") as HTMLElement;
    expect(error).toBeTruthy();
    expect(error.textContent).toContain("None of the tokens of the template was created:");
    expect(callout()!.textContent).not.toContain("These tokens of the template were not created");
    expect(callout()!.querySelectorAll("li").length).toBe(2);
  });

  it("renders nothing for an empty list even when allFailed is set", () => {
    render([], true);

    expect(callout()).toBeNull();
  });
});
