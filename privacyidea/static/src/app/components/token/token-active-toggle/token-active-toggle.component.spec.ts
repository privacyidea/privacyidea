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
import { MatTooltip } from "@angular/material/tooltip";
import { By } from "@angular/platform-browser";
import { AuthService } from "@services/auth/auth.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { TokenService } from "@services/token/token.service";
import { MockTokenService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { grantRights } from "@testing/toolbar-actions";
import { ActiveToggleToken, TokenActiveToggleComponent } from "./token-active-toggle.component";

describe("TokenActiveToggleComponent", () => {
  let fixture: ComponentFixture<TokenActiveToggleComponent>;
  let tokenService: MockTokenService;

  const show = (token: ActiveToggleToken, rights: string[]): void => {
    grantRights(rights);
    fixture.componentRef.setInput("token", token);
    fixture.detectChanges();
  };
  const button = (): HTMLButtonElement | null => fixture.nativeElement.querySelector("button");
  const readOnly = (): HTMLSpanElement | null => fixture.nativeElement.querySelector(":scope > span");

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenActiveToggleComponent],
      providers: [
        TableUtilsService,
        { provide: AuthService, useClass: MockAuthService },
        { provide: TokenService, useClass: MockTokenService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenActiveToggleComponent);
    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
  });

  afterEach(() => jest.clearAllMocks());

  it.each([
    ["disable", true],
    ["enable", false]
  ])("offers the toggle with only the %s right when that is the action for the token", (right, active) => {
    show({ serial: "T-1", active }, [right]);

    expect(button()?.type).toBe("button");
    expect(readOnly()).toBeNull();
  });

  it.each([
    ["enable", true],
    ["disable", false]
  ])("shows the state read-only with only the %s right when the token needs the other one", (right, active) => {
    show({ serial: "T-1", active }, [right]);

    expect(button()).toBeNull();
    expect(readOnly()?.className).not.toContain("clickable");
  });

  it.each([
    ["revoked", { revoked: true }],
    ["locked", { locked: true }]
  ])("shows a %s token read-only with both rights", (_state, flags) => {
    show({ serial: "T-1", active: true, ...flags }, ["enable", "disable"]);

    expect(button()).toBeNull();
    expect(readOnly()?.className).toBe("highlight-disabled");
  });

  it("describes the toggle action with the tooltip and gives the read-only state none", () => {
    show({ serial: "T-1", active: true }, ["disable"]);
    expect(button()?.getAttribute("aria-describedby")).toBeTruthy();

    show({ serial: "T-1", active: true }, []);
    expect(readOnly()?.hasAttribute("aria-describedby")).toBe(false);
  });

  it("shows the tooltip only after the pointer rests on the toggle for half a second", () => {
    show({ serial: "T-1", active: true }, ["disable"]);

    const tooltip = fixture.debugElement.query(By.css("button")).injector.get(MatTooltip);

    expect(tooltip.showDelay).toBe(500);
  });

  it("toggles the token and reports it once the request succeeds", () => {
    const toggled = jest.fn();
    fixture.componentInstance.toggled.subscribe(toggled);
    show({ serial: "T-1", active: true }, ["disable"]);

    button()!.click();

    expect(tokenService.toggleActive).toHaveBeenCalledWith("T-1", true);
    expect(toggled).toHaveBeenCalledTimes(1);
  });
});
