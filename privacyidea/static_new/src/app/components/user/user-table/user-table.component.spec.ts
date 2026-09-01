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

import { provideHttpClient } from "@angular/common/http";
import { ActivatedRoute } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { RealmService } from "@services/realm/realm.service";
import { ResolverService } from "@services/resolver/resolver.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { UserData, UserService } from "@services/user/user.service";
import {
  MockContentService,
  MockLocalService,
  MockNotificationService,
  MockRealmService,
  MockTableUtilsService,
  MockUserService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockResolverService } from "@testing/mock-services/mock-resolver-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { expectsTableStateGating } from "@testing/table-state-gating";
import { of } from "rxjs";
import { UserTableComponent } from "./user-table.component";

describe("UserTableComponent", () => {
  let component: UserTableComponent;
  let fixture: ComponentFixture<UserTableComponent>;
  let mockUserService: MockUserService;
  let mockTableUtilsService: MockTableUtilsService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useClass: MockAuthService },
        provideHttpClient(),
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({ id: "123" })
          }
        },
        { provide: UserService, useClass: MockUserService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: ContentService, useClass: MockContentService },
        { provide: ResolverService, useClass: MockResolverService },
        { provide: RealmService, useClass: MockRealmService },
        MockLocalService,
        MockNotificationService
      ],
      imports: [UserTableComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(UserTableComponent);
    component = fixture.componentInstance;
    mockUserService = TestBed.inject(UserService) as unknown as MockUserService;
    mockTableUtilsService = TestBed.inject(TableUtilsService) as unknown as MockTableUtilsService;
    fixture.detectChanges();
  });

  it("gates the table on its read right, row count and filter", () => {
    expectsTableStateGating({
      state: component.tableState,
      right: "userlist"
    });
  });

  it("stops a user load that hangs, and reports it on the panel", () => {
    const authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["userlist"] });
    // A request is out and nothing has come back for it yet.
    mockUserService.usersResource.set(undefined as never);
    mockUserService.usersResource.isLoading.set(true);
    expect(component.tableState.status()).toBe("loading");

    component.tableState.cancel();

    expect(mockUserService.usersResource.hasValue()).toBe(false);
    expect(mockUserService.usersResource.isLoading()).toBe(false);
    expect(component.tableState.status()).toBe("cancelled");
    expect(component.tableState.showTable()).toBe(false);

    component.tableState.retry();

    expect(mockUserService.usersResource.reload).toHaveBeenCalled();
    expect(component.tableState.status()).toBe("loading");
  });

  describe("the resolvers the server could not query", () => {
    // The names run together in one sentence, so the separators matter as much as the names.
    const warningText = (): string =>
      (fixture.nativeElement.querySelector(".resolver-warning")?.textContent ?? "").replace(/\s+/g, " ").trim();

    const resolverLinks = (): HTMLAnchorElement[] =>
      Array.from(fixture.nativeElement.querySelectorAll(".resolver-warning a"));

    const allowResolverRead = (allowed: boolean) => {
      const authService = TestBed.inject(AuthService) as unknown as MockAuthService;
      authService.authData.set({
        ...MockAuthService.MOCK_AUTH_DATA,
        rights: allowed ? ["userlist", "resolverread"] : ["userlist"]
      });
    };

    it("stays out of the way while every resolver answered", () => {
      expect(fixture.nativeElement.querySelector(".resolver-warning")).toBeNull();
    });

    it("names them, and points each one at its configuration", () => {
      allowResolverRead(true);
      mockUserService.skippedResolvers.set(["ldap1", "sql1"]);
      fixture.detectChanges();

      expect(warningText()).toContain("incomplete: ldap1, sql1");
      const links = resolverLinks();
      expect(links.map((link) => link.textContent?.trim())).toEqual(["ldap1", "sql1"]);
      expect(links.map((link) => link.getAttribute("href"))).toEqual([
        ROUTE_PATHS.USERS_RESOLVERS_DETAILS + "ldap1",
        ROUTE_PATHS.USERS_RESOLVERS_DETAILS + "sql1"
      ]);
    });

    it("names them as plain text where their configuration may not be read", () => {
      allowResolverRead(false);
      mockUserService.skippedResolvers.set(["ldap1", "sql1"]);
      fixture.detectChanges();

      expect(warningText()).toContain("incomplete: ldap1, sql1");
      expect(resolverLinks()).toHaveLength(0);
    });
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("onClickUsername stores username and the selected realm", () => {
    mockUserService.selectedUserRealm.set("themis");
    component.onClickUsername({ username: "alice" } as never);

    expect(mockUserService.detailsUser().username).toBe("alice");
    expect(mockUserService.detailsUser().realm).toBe("themis");
  });

  describe("keyword-less client-side search", () => {
    const users = [
      { username: "alice", email: "alice@acme.test", givenname: "Alice" },
      { username: "bob", email: "bob@other.test", givenname: "Bob" }
    ] as UserData[];

    beforeEach(() => {
      mockUserService.usersResource.set(MockPiResponse.fromValue(users) as never);
    });

    // Read the data signal directly rather than running full template change detection: the
    // template's clear-button binding reads the live input value and trips checkNoChanges in tests.
    const namesFor = (rawFilter: string) => {
      mockUserService.activeFilter.set(new FilterValue({ value: rawFilter }));
      return component.usersDataSource().data.map((u) => u.username);
    };

    it("derives free-text terms from the keyword-less part of the filter", () => {
      mockUserService.activeFilter.set(new FilterValue({ value: "alice username: bob" }));
      expect(component.freeTextTerms()).toEqual(["alice"]);

      mockUserService.activeFilter.set(new FilterValue({ value: "username: bob" }));
      expect(component.freeTextTerms()).toEqual([]);
    });

    it("filters the loaded users across all columns for a bare term", () => {
      expect(namesFor("acme")).toEqual(["alice"]); // matches email
      expect(namesFor("bob")).toEqual(["bob"]); // matches username
      expect(component.totalLength()).toBe(1);
    });

    it("does not client-filter when only column keywords are used", () => {
      expect(namesFor("username: bob")).toEqual(["alice", "bob"]);
    });

    it("keeps the last count and rows while the users resource has no value (loading)", () => {
      mockUserService.activeFilter.set(new FilterValue({ value: "bob" }));
      expect(component.totalLength()).toBe(1);
      expect(component.usersDataSource().data.map((u) => u.username)).toEqual(["bob"]);

      // Simulate a reload where the resource temporarily has no value: free-text filtering is
      // skipped and the previously computed count and rows are retained.
      mockUserService.usersResource.set(undefined as never);
      expect(component.totalLength()).toBe(1);
      expect(component.usersDataSource().data.map((u) => u.username)).toEqual(["bob"]);
    });

    it("resets the filter when leaving the page", () => {
      mockUserService.activeFilter.set(new FilterValue({ value: "alice" }));
      component.ngOnDestroy();
      expect(mockUserService.clearFilter).toHaveBeenCalled();
    });
  });

  it("pageSizeOptions should add custom page size if not included in default options", () => {
    const defaultOptions = [5, 10, 25, 50];
    mockTableUtilsService.pageSizeOptions.set(defaultOptions);
    expect(component.pageSizeOptions()).toEqual(defaultOptions);

    // Check custom page size is added but does not mutate the options from the service
    const customOptions = [5, 10, 15, 25, 50];
    mockUserService.pageSize.set(15);
    expect(component.pageSizeOptions()).toEqual(customOptions);
    expect(mockTableUtilsService.pageSizeOptions()).toEqual(defaultOptions);

    // custom page size should still be included if selected pageSize changes
    mockUserService.pageSize.set(10);
    expect(component.pageSizeOptions()).toEqual(customOptions);
  });
});
