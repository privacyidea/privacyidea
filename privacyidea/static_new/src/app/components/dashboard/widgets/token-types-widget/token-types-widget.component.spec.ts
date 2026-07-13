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
import { TokenCountParams, TokenService, TokenTypeKey } from "@services/token/token.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockTokenService } from "@testing/mock-services/mock-token-service";
import { of, Subject } from "rxjs";
import { TokenTypesWidgetComponent } from "./token-types-widget.component";

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

const COUNTS_BY_TYPE: Partial<Record<string, number>> = { hotp: 55, totp: 12, push: 0 };

describe("TokenTypesWidgetComponent", () => {
  let fixture: ComponentFixture<TokenTypesWidgetComponent>;
  let component: TokenTypesWidgetComponent;
  let authMock: MockAuthService;
  let tokenMock: MockTokenService;

  const instance: WidgetInstance = { id: "token-types-1", type: "token-types", x: 0, y: 0, cols: 6, rows: 5 };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenTypesWidgetComponent],
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
    tokenMock.getTokenCount.mockImplementation((params: TokenCountParams = {}) =>
      of(makeCountResponse(params.type ? (COUNTS_BY_TYPE[params.type] ?? 0) : 0))
    );

    fixture = TestBed.createComponent(TokenTypesWidgetComponent);
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
    expect(TokenTypesWidgetComponent.type).toBe("token-types");
    expect(TokenTypesWidgetComponent.title).toBeTruthy();
    expect(TokenTypesWidgetComponent.icon).toBe("shield");
    expect(TokenTypesWidgetComponent.headerIcon).toBeTruthy();
  });

  it("should list token types with a non-zero count, sorted by count descending", () => {
    expect(component.typeCounts()).toEqual([
      { key: "hotp", name: "HOTP", count: 55 },
      { key: "totp", name: "TOTP", count: 12 }
    ]);
  });

  it("should render a link per non-zero token type and hide zero-count types", () => {
    const text = fixture.nativeElement.textContent;
    expect(text).toContain("HOTP");
    expect(text).toContain("TOTP");
    expect(text).not.toContain("PUSH");
  });

  it("should set a type preset filter when a type link is clicked", () => {
    component.showType("hotp");
    expect(tokenMock.presetFilter()?.getValueOfKey("type")).toBe("hotp");
  });

  it("should reload only previously non-zero types on dashboard re-entry", () => {
    tokenMock.getTokenCount.mockClear();

    const fixture2 = TestBed.createComponent(TokenTypesWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();

    const reentryTypes = tokenMock.getTokenCount.mock.calls
      .map(([params]) => (params as TokenCountParams | undefined)?.type)
      .filter((type): type is TokenTypeKey => type !== undefined);

    expect(reentryTypes.length).toBe(2);
    expect(reentryTypes).toEqual(expect.arrayContaining(["hotp", "totp"]));
    expect(reentryTypes).not.toContain("push");
    fixture2.destroy();
  });

  it("should reload all types including previous zero-count types on manual refresh", () => {
    tokenMock.getTokenCount.mockClear();

    component.reload();

    const refreshedTypes = tokenMock.getTokenCount.mock.calls
      .map(([params]) => (params as TokenCountParams | undefined)?.type)
      .filter((type): type is TokenTypeKey => type !== undefined);

    expect(refreshedTypes).toContain("hotp");
    expect(refreshedTypes).toContain("totp");
    expect(refreshedTypes).toContain("push");
  });

  it("should keep existing type counts visible while partial reload updates are arriving", () => {
    const store = TestBed.inject(DashboardDataStore);
    store.invalidate("dashboard:tokens:by_type");

    const initialCounts: Partial<Record<string, number>> = { hotp: 13, push: 2, spass: 1 };
    tokenMock.getTokenCount.mockImplementation((params: TokenCountParams = {}) =>
      of(makeCountResponse(params.type ? (initialCounts[params.type] ?? 0) : 0))
    );

    const fixture1 = TestBed.createComponent(TokenTypesWidgetComponent);
    fixture1.componentRef.setInput("instance", instance);
    fixture1.detectChanges();

    const pendingPush = new Subject<ReturnType<typeof makeCountResponse>>();
    const pendingSpass = new Subject<ReturnType<typeof makeCountResponse>>();
    tokenMock.getTokenCount.mockImplementation((params: TokenCountParams = {}) => {
      if (params.type === "hotp") {
        return of(makeCountResponse(12));
      }
      if (params.type === "push") {
        return pendingPush;
      }
      if (params.type === "spass") {
        return pendingSpass;
      }
      return of(makeCountResponse(0));
    });

    const fixture2 = TestBed.createComponent(TokenTypesWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();

    const component2 = fixture2.componentInstance;
    expect(component2.typeCounts()).toEqual([
      { key: "hotp", name: "HOTP", count: 12 },
      { key: "push", name: "PUSH", count: 2 },
      { key: "spass", name: "SPass", count: 1 }
    ]);

    pendingPush.next(makeCountResponse(2));
    pendingPush.complete();
    pendingSpass.next(makeCountResponse(1));
    pendingSpass.complete();
    fixture2.destroy();
    fixture1.destroy();
  });

  it("should show an empty hint when no token type has tokens", () => {
    const store = TestBed.inject(DashboardDataStore);
    store.invalidate();
    tokenMock.getTokenCount.mockImplementation(() => of(makeCountResponse(0)));

    const fixture2 = TestBed.createComponent(TokenTypesWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();

    expect(fixture2.nativeElement.querySelector("table")).toBeNull();
    expect(fixture2.nativeElement.textContent).toContain("No tokens");
    fixture2.destroy();
  });

  it("should render nothing when tokenlist right is missing", () => {
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: [] });

    const fixture2 = TestBed.createComponent(TokenTypesWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();

    expect(fixture2.nativeElement.querySelector("table")).toBeNull();
    fixture2.destroy();
  });

  it("should skip reloading when every previously loaded type has a zero count", () => {
    const store = TestBed.inject(DashboardDataStore);
    store.invalidate();
    tokenMock.getTokenCount.mockImplementation(() => of(makeCountResponse(0)));

    const fixture1 = TestBed.createComponent(TokenTypesWidgetComponent);
    fixture1.componentRef.setInput("instance", instance);
    fixture1.detectChanges();

    tokenMock.getTokenCount.mockClear();

    const fixture2 = TestBed.createComponent(TokenTypesWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();

    expect(tokenMock.getTokenCount).not.toHaveBeenCalled();
    fixture2.destroy();
    fixture1.destroy();
  });

  it("should report partial data while some but not all token types have loaded", () => {
    const store = TestBed.inject(DashboardDataStore);
    store.invalidate();

    const pending = new Subject<ReturnType<typeof makeCountResponse>>();
    tokenMock.getTokenCount.mockImplementation((params: TokenCountParams = {}) =>
      params.type === "hotp" ? of(makeCountResponse(5)) : pending.asObservable()
    );

    const fixture2 = TestBed.createComponent(TokenTypesWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();

    expect(fixture2.componentInstance.hasPartialData()).toBe(true);
    expect(fixture2.componentInstance.loading()).toBe(true);
    fixture2.destroy();
  });

  it("should report not loading once the widget is denied or in error", () => {
    component.state.set("denied");
    expect(component.loading()).toBe(false);

    component.state.set("error");
    expect(component.loading()).toBe(false);
  });

  it("should set the state to loading while the request is still in flight", () => {
    const store = TestBed.inject(DashboardDataStore);
    store.invalidate();
    tokenMock.getTokenCount.mockImplementation(() => new Subject().asObservable());

    const fixture2 = TestBed.createComponent(TokenTypesWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();

    expect(fixture2.componentInstance.state()).toBe("loading");
    fixture2.destroy();
  });

  it("should set the state to error when the request fails", () => {
    const store = TestBed.inject(DashboardDataStore);
    store.invalidate();
    const subject = new Subject<ReturnType<typeof makeCountResponse>>();
    tokenMock.getTokenCount.mockImplementation(() => subject.asObservable());

    const fixture2 = TestBed.createComponent(TokenTypesWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();
    subject.error(new Error("boom"));
    fixture2.detectChanges();

    expect(fixture2.componentInstance.state()).toBe("error");
    fixture2.destroy();
  });
});
