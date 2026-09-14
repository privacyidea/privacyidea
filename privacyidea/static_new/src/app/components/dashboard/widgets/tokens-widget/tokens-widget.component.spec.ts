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
import { DashboardLayoutService } from "@services/dashboard/dashboard-layout.service";
import { RealmService } from "@services/realm/realm.service";
import { TokenCountParams, TokenOwnerCount, TokenService } from "@services/token/token.service";
import { UserData, UserListResponseDetail, UserService } from "@services/user/user.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockRealmService } from "@testing/mock-services/mock-realm-service";
import { MockTokenService } from "@testing/mock-services/mock-token-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { MockUserService } from "@testing/mock-services/mock-user-service";
import { of, Subject, throwError } from "rxjs";
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

function makeOwnerCountResponse(ownerCount: TokenOwnerCount) {
  return MockPiResponse.fromValue<TokenOwnerCount>(ownerCount);
}

function buildUser(username: string, resolver: string): UserData {
  return {
    username,
    userid: username,
    description: "",
    editable: true,
    email: "",
    givenname: "",
    surname: "",
    mobile: "",
    phone: "",
    resolver
  };
}

describe("TokensWidgetComponent", () => {
  let fixture: ComponentFixture<TokensWidgetComponent>;
  let component: TokensWidgetComponent;
  let authMock: MockAuthService;
  let tokenMock: MockTokenService;
  let userMock: MockUserService;
  let realmMock: MockRealmService;
  let layoutService: DashboardLayoutService;

  const instance: WidgetInstance = { id: "tokens-1", type: "tokens", x: 0, y: 0, cols: 8, rows: 5 };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokensWidgetComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: AuthService, useClass: MockAuthService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: UserService, useClass: MockUserService },
        { provide: RealmService, useClass: MockRealmService }
      ]
    }).compileComponents();

    authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["tokenlist", "userlist"] });

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
    tokenMock.getTokenOwnerCount.mockReturnValue(of(makeOwnerCountResponse({ count: 0, by_resolver: {} })));

    userMock = TestBed.inject(UserService) as unknown as MockUserService;
    userMock.fetchUsernames.mockReturnValue(of(MockPiResponse.fromValue<UserData[]>([])));

    realmMock = TestBed.inject(RealmService) as unknown as MockRealmService;
    realmMock.realmOptions.set([]);

    layoutService = TestBed.inject(DashboardLayoutService);

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
    expect(TokensWidgetComponent.defaultSize).toEqual({ cols: 6, rows: 7 });
    expect(TokensWidgetComponent.minSize).toEqual({ cols: 4, rows: 3 });
    expect(TokensWidgetComponent.maxSize).toEqual({ cols: 12, rows: 11 });
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
    expect(labels).toContain("Users with tokens");
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

  it("should set the state to loading while the requests are still in flight", () => {
    TestBed.inject(DashboardDataStore).invalidate();
    tokenMock.getTokenCount.mockReturnValue(new Subject().asObservable());

    const fixture2 = TestBed.createComponent(TokensWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();

    expect(fixture2.componentInstance.state()).toBe("loading");
    fixture2.destroy();
  });

  it("should set the state to error when a request fails", () => {
    TestBed.inject(DashboardDataStore).invalidate();
    tokenMock.getTokenCount.mockReturnValue(throwError(() => new Error("boom")));

    const fixture2 = TestBed.createComponent(TokensWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();

    expect(fixture2.componentInstance.state()).toBe("error");
    fixture2.destroy();
  });

  it("should invalidate the cache and reload on reload()", () => {
    tokenMock.getTokenCount.mockClear();

    component.reload();

    expect(tokenMock.getTokenCount).toHaveBeenCalledTimes(5);
  });

  describe("realm switch", () => {
    // The header actions template is only rendered once WidgetFrameComponent projects it via
    // ngTemplateOutlet (covered there); here the signal the template's @if reads is what matters.
    it("carries no realm options to switch between until the realm service loads them", () => {
      expect(component.realmOptions()).toEqual([]);
    });

    it("exposes the realm options once the realm service has them", () => {
      realmMock.realmOptions.set(["realm1", "realm2"]);
      expect(component.realmOptions()).toEqual(["realm1", "realm2"]);
    });

    it("defaults to every realm when the instance carries no setting", () => {
      expect(component.realm()).toBe("");
      expect(component.realmLabel()).toBe("All realms");
    });

    it("reads the realm from the widget instance settings", () => {
      const scoped: WidgetInstance = { ...instance, settings: { realm: "realm1" } };
      const fixture2 = TestBed.createComponent(TokensWidgetComponent);
      fixture2.componentRef.setInput("instance", scoped);
      fixture2.detectChanges();

      expect(fixture2.componentInstance.realm()).toBe("realm1");
      expect(fixture2.componentInstance.realmLabel()).toBe("realm1");
      fixture2.destroy();
    });

    it("stores the picked realm on the widget instance and reloads scoped counts", () => {
      const updateSpy = jest.spyOn(layoutService, "updateWidgetSettings");
      tokenMock.getTokenCount.mockClear();

      component.selectRealm("realm1");

      expect(updateSpy).toHaveBeenCalledWith("tokens-1", { realm: "realm1" });
      expect(tokenMock.getTokenCount).toHaveBeenCalledWith(expect.objectContaining({ tokenrealm: "realm1" }));
    });

    it("does nothing when the picked realm is already selected", () => {
      const updateSpy = jest.spyOn(layoutService, "updateWidgetSettings");
      component.selectRealm("");
      expect(updateSpy).not.toHaveBeenCalled();
    });

    it("scopes showAllTokens/showKind/showUnassigned to the selected realm", () => {
      const scoped: WidgetInstance = { ...instance, settings: { realm: "realm1" } };
      const fixture2 = TestBed.createComponent(TokensWidgetComponent);
      fixture2.componentRef.setInput("instance", scoped);
      fixture2.detectChanges();

      fixture2.componentInstance.showAllTokens();
      expect(tokenMock.presetFilter()?.getValueOfKey("tokenrealm")).toBe("realm1");
      fixture2.destroy();
    });
  });

  describe("user counts", () => {
    it("counts distinct (resolver, username) pairs and subtracts the owner count", () => {
      const store = TestBed.inject(DashboardDataStore);
      store.invalidate();
      tokenMock.getTokenOwnerCount.mockReturnValue(
        of(makeOwnerCountResponse({ count: 2, by_resolver: { resolver1: 2 } }))
      );
      userMock.fetchUsernames.mockReturnValue(
        of(MockPiResponse.fromValue<UserData[]>([buildUser("alice", "resolver1"), buildUser("bob", "resolver1")]))
      );

      const fixture2 = TestBed.createComponent(TokensWidgetComponent);
      fixture2.componentRef.setInput("instance", instance);
      fixture2.detectChanges();

      expect(fixture2.componentInstance.userCounts()).toEqual({
        withTokens: 2,
        withoutTokens: 0,
        skippedResolvers: []
      });
      fixture2.destroy();
    });

    it("excludes skipped resolvers from both counts so the difference stays meaningful", () => {
      const store = TestBed.inject(DashboardDataStore);
      store.invalidate();
      tokenMock.getTokenOwnerCount.mockReturnValue(
        of(makeOwnerCountResponse({ count: 12, by_resolver: { reachable: 2, broken: 10 } }))
      );
      userMock.fetchUsernames.mockReturnValue(
        of(
          MockPiResponse.fromValue<UserData[], UserListResponseDetail>(
            [buildUser("alice", "reachable"), buildUser("bob", "reachable")],
            { skipped_resolvers: ["broken"] }
          )
        )
      );

      const fixture2 = TestBed.createComponent(TokensWidgetComponent);
      fixture2.componentRef.setInput("instance", instance);
      fixture2.detectChanges();

      expect(fixture2.componentInstance.userCounts()).toEqual({
        withTokens: 2,
        withoutTokens: 0,
        skippedResolvers: ["broken"]
      });
      expect(fixture2.nativeElement.textContent).toContain("broken");
      fixture2.destroy();
    });

    it("shows an em dash for both rows while the owner count has not arrived", () => {
      const store = TestBed.inject(DashboardDataStore);
      store.invalidate();
      tokenMock.getTokenOwnerCount.mockReturnValue(new Subject().asObservable());

      const fixture2 = TestBed.createComponent(TokensWidgetComponent);
      fixture2.componentRef.setInput("instance", instance);
      fixture2.detectChanges();

      expect(fixture2.componentInstance.withTokensLabel()).toBe("—");
      expect(fixture2.componentInstance.withoutTokensLabel()).toBe("—");
      fixture2.destroy();
    });

    it("does not fail the widget state when the owner count endpoint errors", () => {
      const store = TestBed.inject(DashboardDataStore);
      store.invalidate();
      tokenMock.getTokenOwnerCount.mockReturnValue(throwError(() => new Error("boom")));

      const fixture2 = TestBed.createComponent(TokensWidgetComponent);
      fixture2.componentRef.setInput("instance", instance);
      fixture2.detectChanges();

      expect(fixture2.componentInstance.state()).toBe("ready");
      expect(fixture2.componentInstance.withTokensLabel()).toBe("—");
      fixture2.destroy();
    });

    it("does not show the without-tokens row or fetch usernames without the userlist right", () => {
      const store = TestBed.inject(DashboardDataStore);
      store.invalidate();
      authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["tokenlist"] });
      userMock.fetchUsernames.mockClear();

      const fixture2 = TestBed.createComponent(TokensWidgetComponent);
      fixture2.componentRef.setInput("instance", instance);
      fixture2.detectChanges();

      expect(fixture2.componentInstance.canListUsers()).toBe(false);
      expect(userMock.fetchUsernames).not.toHaveBeenCalled();
      const labels = Array.from(fixture2.nativeElement.querySelectorAll("td:first-child")).map((td) =>
        (td as Element).textContent?.trim()
      );
      expect(labels).toContain("Users with tokens");
      expect(labels).not.toContain("Users without tokens");
      fixture2.destroy();
    });

    it("only links the user counts once a realm is picked", () => {
      expect(component.canLinkUsers()).toBe(false);

      const scoped: WidgetInstance = { ...instance, settings: { realm: "realm1" } };
      const fixture2 = TestBed.createComponent(TokensWidgetComponent);
      fixture2.componentRef.setInput("instance", scoped);
      fixture2.detectChanges();

      expect(fixture2.componentInstance.canLinkUsers()).toBe(true);
      fixture2.destroy();
    });

    it("sets a has_tokens preset filter on the user service when a user count is clicked", () => {
      component.showUsers(true);
      expect(userMock.presetFilter()?.getValueOfKey("has_tokens")).toBe("True");

      component.showUsers(false);
      expect(userMock.presetFilter()?.getValueOfKey("has_tokens")).toBe("False");
    });
  });
});
