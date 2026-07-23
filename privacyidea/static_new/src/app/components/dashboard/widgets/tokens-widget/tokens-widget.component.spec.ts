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
import { provideZonelessChangeDetection } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";
import { DashboardWidget, WidgetInstance } from "@models/dashboard";
import { AuthService } from "@services/auth/auth.service";
import { DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { TokenCountParams, TokenService } from "@services/token/token.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockTokenService } from "@testing/mock-services/mock-token-service";
import { of } from "rxjs";
import { TokensWidgetComponent } from "./tokens-widget.component";

function makeCountResponse(count: number) {
  return {
    id: 1,
    jsonrpc: "2.0",
    signature: "",
    time: 0,
    version: "",
    versionnumber: "",
    detail: {},
    result: { status: true, value: { count, current: 1, tokens: [] } }
  };
}

describe("TokensWidgetComponent", () => {
  let fixture: ComponentFixture<TokensWidgetComponent>;
  let component: TokensWidgetComponent;
  let authMock: MockAuthService;
  let tokenMock: MockTokenService;

  const instance: WidgetInstance = { id: "tokens-1", type: "tokens", x: 0, y: 0, cols: 8, rows: 5 };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokensWidgetComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: AuthService, useClass: MockAuthService },
        { provide: TokenService, useClass: MockTokenService }
      ]
    }).compileComponents();

    authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["tokenlist"] });

    tokenMock = TestBed.inject(TokenService) as unknown as MockTokenService;
    tokenMock.getTokenCount.mockImplementation((params: TokenCountParams = {}) => {
      const { infokey, infovalue, assigned } = params;
      if (infokey === "tokenkind" && infovalue === "hardware" && assigned === "False") {
        return of(makeCountResponse(3));
      }
      if (infokey === "tokenkind" && infovalue === "software" && assigned === "False") {
        return of(makeCountResponse(7));
      }
      if (infokey === "tokenkind" && infovalue === "hardware") {
        return of(makeCountResponse(12));
      }
      if (infokey === "tokenkind" && infovalue === "software") {
        return of(makeCountResponse(25));
      }
      return of(makeCountResponse(100));
    });

    fixture = TestBed.createComponent(TokensWidgetComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("instance", instance);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should extend the DashboardWidget base", () => {
    expect(component).toBeInstanceOf(DashboardWidget);
  });

  it("should override the static metadata", () => {
    expect(TokensWidgetComponent.type).toBe("tokens");
    expect(TokensWidgetComponent.title).toBeTruthy();
    expect(TokensWidgetComponent.icon).toBe("shield");
  });

  it("should override the static size constraints", () => {
    expect(TokensWidgetComponent.defaultSize).toEqual({ cols: 6, rows: 5 });
    expect(TokensWidgetComponent.minSize).toEqual({ cols: 4, rows: 3 });
    expect(TokensWidgetComponent.maxSize).toEqual({ cols: 12, rows: 9 });
  });

  it("should render the token count rows when the right is granted", () => {
    const labels = Array.from(fixture.nativeElement.querySelectorAll("td:first-child")).map((td) =>
      (td as Element).textContent?.trim()
    );
    expect(labels).toContain("Total");
    expect(labels).toContain("Hardware");
    expect(labels).toContain("Software");
    expect(labels).toContain("Unassigned Hardware");
    expect(labels).toContain("Unassigned Software");
  });

  it("should display the fetched counts", () => {
    const cells = fixture.nativeElement.querySelectorAll("td:last-child") as NodeListOf<Element>;
    const values = Array.from(cells).map((td) => td.textContent?.trim());
    expect(values).toContain("100");
    expect(values).toContain("12");
    expect(values).toContain("25");
    expect(values).toContain("3");
    expect(values).toContain("7");
  });

  it("should hide the Hardware/Software rows when the count is 0 or equals the total", () => {
    const store = TestBed.inject(DashboardDataStore);
    store.invalidate();
    tokenMock.getTokenCount.mockImplementation((params: TokenCountParams = {}) => {
      const { infokey, infovalue } = params;
      if (infokey === "tokenkind" && infovalue === "hardware") {
        return of(makeCountResponse(0));
      }
      if (infokey === "tokenkind" && infovalue === "software") {
        return of(makeCountResponse(17));
      }
      return of(makeCountResponse(17));
    });

    const fixture2 = TestBed.createComponent(TokensWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();

    const labels = Array.from(fixture2.nativeElement.querySelectorAll("td:first-child")).map((td) =>
      (td as Element).textContent?.trim()
    );
    expect(labels).toContain("Total");
    expect(labels).not.toContain("Hardware");
    expect(labels).not.toContain("Software");
    fixture2.destroy();
  });

  it("should render 0 counts as plain text, not as a link", () => {
    const store = TestBed.inject(DashboardDataStore);
    store.invalidate();
    tokenMock.getTokenCount.mockImplementation(() => of(makeCountResponse(0)));

    const fixture2 = TestBed.createComponent(TokensWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();

    expect(fixture2.nativeElement.querySelector("a")).toBeNull();
    fixture2.destroy();
  });

  it("should set a tokenkind preset filter when a kind count is clicked", () => {
    component.showKind("hardware");
    const filter = tokenMock.presetFilter();
    expect(filter?.getValueOfKey("infokey")).toBe("tokenkind");
    expect(filter?.getValueOfKey("infovalue")).toBe("hardware");
    expect(filter?.getValueOfKey("assigned")).toBeUndefined();
  });

  it("should add assigned=False to the preset filter for unassigned counts", () => {
    component.showKind("software", true);
    const filter = tokenMock.presetFilter();
    expect(filter?.getValueOfKey("infovalue")).toBe("software");
    expect(filter?.getValueOfKey("assigned")).toBe("False");
  });

  it("should set an empty preset filter when the total is clicked", () => {
    component.showAllTokens();
    expect(tokenMock.presetFilter()?.isEmpty).toBe(true);
  });

  it("should show a single combined 'Unassigned' row when only one token kind exists", () => {
    const store = TestBed.inject(DashboardDataStore);
    store.invalidate();
    tokenMock.getTokenCount.mockImplementation((params: TokenCountParams = {}) => {
      const { infokey, infovalue, assigned } = params;
      if (infokey === "tokenkind" && infovalue === "hardware") {
        return of(makeCountResponse(0));
      }
      if (infokey === "tokenkind" && infovalue === "software" && assigned === "False") {
        return of(makeCountResponse(13));
      }
      if (infokey === "tokenkind" && infovalue === "software") {
        return of(makeCountResponse(17));
      }
      return of(makeCountResponse(17));
    });

    const fixture2 = TestBed.createComponent(TokensWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();

    const labels = Array.from(fixture2.nativeElement.querySelectorAll("td:first-child")).map((td) =>
      (td as Element).textContent?.trim()
    );
    expect(labels).toContain("Unassigned");
    expect(labels).not.toContain("Unassigned Hardware");
    expect(labels).not.toContain("Unassigned Software");
    fixture2.destroy();
  });

  it("should set an assigned=False preset filter (without a kind) for the combined Unassigned row", () => {
    component.showUnassigned();
    const filter = tokenMock.presetFilter();
    expect(filter?.getValueOfKey("assigned")).toBe("False");
    expect(filter?.getValueOfKey("infokey")).toBeUndefined();
  });

  it("should render nothing when tokenlist right is missing", async () => {
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: [] });

    const fixture2 = TestBed.createComponent(TokensWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();

    expect(fixture2.nativeElement.querySelector("table")).toBeNull();
    fixture2.destroy();
  });
});
