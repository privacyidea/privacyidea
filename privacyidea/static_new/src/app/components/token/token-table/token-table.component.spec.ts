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
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { provideRouter } from "@angular/router";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatDialog } from "@angular/material/dialog";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuditService } from "@services/audit/audit.service";
import { AuthService, JwtData } from "@services/auth/auth.service";
import { ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { DialogService } from "@services/dialog/dialog.service";
import { DocumentationService } from "@services/documentation/documentation.service";
import { RealmService } from "@services/realm/realm.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { TokenDetails, TokenService } from "@services/token/token.service";
import { PageEvent } from "@angular/material/paginator";
import { Sort } from "@angular/material/sort";
import {
  MockAuditService,
  MockContainerService,
  MockContentService,
  MockDocumentationService,
  MockLocalService,
  MockNotificationService,
  MockRealmService,
  MockTableUtilsService,
  MockTokenService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { of } from "rxjs";
import { TokenTableComponent } from "./token-table.component";
import { TokenTableSelfServiceComponent } from "./token-table.self-service.component";

class MatDialogMock {
  result = { confirmed: true };
  open = jest.fn(() => ({
    afterClosed: () => of(this.result)
  }));
}

describe("TokenTableComponent + TokenTableSelfServiceComponent", () => {
  let tableFixture: ComponentFixture<TokenTableComponent>;
  let table: TokenTableComponent;

  let tokenService: MockTokenService;
  let authServiceMock: MockAuthService;
  let tableUtilsService: MockTableUtilsService;
  let contentServiceMock: MockContentService;

  beforeAll(() => {
    jest.spyOn(console, "warn").mockReturnValue();
  });

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenTableComponent, TokenTableSelfServiceComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: TokenService, useClass: MockTokenService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: ContentService, useClass: MockContentService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: DocumentationService, useClass: MockDocumentationService },
        { provide: AuditService, useClass: MockAuditService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: MatDialog, useClass: MatDialogMock },
        { provide: RealmService, useClass: MockRealmService },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    tableFixture = TestBed.createComponent(TokenTableComponent);
    table = tableFixture.componentInstance;

    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    tableUtilsService = TestBed.inject(TableUtilsService) as unknown as MockTableUtilsService;
    contentServiceMock = TestBed.inject(ContentService) as unknown as MockContentService;

    tokenService.toggleActive.mockReturnValue(of({}));
    tokenService.resetFailCount.mockReturnValue(of(null));
    authServiceMock.actionAllowed.mockImplementation((action: string) =>
      authServiceMock.jwtData()?.rights?.includes(action)
    );

    tableFixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("TokenTableComponent should create", () => {
    expect(table).toBeTruthy();
  });

  it("TokenTableSelfServiceComponent should create", () => {
    const selfFixture = TestBed.createComponent(TokenTableSelfServiceComponent);
    expect(selfFixture.componentInstance).toBeTruthy();
  });

  it("isAllSelected/toggleAllRows/toggleRow work as expected", () => {
    const tokens = [{ serial: "T-1" } as TokenDetails, { serial: "T-2" } as TokenDetails];
    tokenService.tokenResourceValue.set({
      tokens,
      count: 2,
      current: 1
    });
    tableFixture.detectChanges();

    expect(table.isAllSelected()).toBe(false);

    table.toggleAllRows();
    expect(table.tokenSelection()).toEqual(tokens);
    expect(table.isAllSelected()).toBe(true);

    table.toggleRow(tokens[0]);
    expect(table.tokenSelection()).toEqual([tokens[1]]);
    expect(table.isAllSelected()).toBe(false);

    table.toggleRow(tokens[0]);
    expect(table.tokenSelection()).toEqual(tokens.reverse());

    table.toggleAllRows();
    expect(table.tokenSelection()).toEqual([]);
  });

  it("toggleActive calls service and reloads when allowed & not revoked/locked", () => {
    const t = { serial: "A", active: true, revoked: false, locked: false } as TokenDetails;
    authServiceMock.jwtData.set({
      ...authServiceMock.jwtData(),
      rights: ["disable", "enable"]
    } as JwtData);

    table.toggleActive(t);

    expect(tokenService.toggleActive).toHaveBeenCalledWith("A", true);
    expect(tokenService.tokenResource.reload).toHaveBeenCalledTimes(1);
  });

  it("toggleActive does nothing if action not allowed", () => {
    const t = { serial: "A", active: true, revoked: false, locked: false } as TokenDetails;
    authServiceMock.jwtData.set({
      ...authServiceMock.jwtData(),
      rights: []
    } as JwtData);

    table.toggleActive(t);

    expect(tokenService.toggleActive).not.toHaveBeenCalled();
    expect(tokenService.tokenResource.reload).not.toHaveBeenCalled();
  });

  it("toggleActive does nothing if revoked or locked", () => {
    authServiceMock.jwtData.set({
      ...authServiceMock.jwtData(),
      rights: ["disable", "enable"]
    } as JwtData);

    table.toggleActive({ serial: "X", active: true, revoked: true, locked: false } as TokenDetails);
    table.toggleActive({ serial: "Y", active: false, revoked: false, locked: true } as TokenDetails);

    expect(tokenService.toggleActive).not.toHaveBeenCalled();
  });

  it("resetFailCount calls service and reloads when allowed & not revoked/locked", () => {
    const t = { serial: "B", revoked: false, locked: false } as TokenDetails;
    authServiceMock.jwtData.set({
      ...authServiceMock.jwtData(),
      rights: ["reset"]
    } as JwtData);

    table.resetFailCount(t);

    expect(tokenService.resetFailCount).toHaveBeenCalledWith("B");
    expect(tokenService.tokenResource.reload).toHaveBeenCalledTimes(1);
  });

  it("resetFailCount does nothing when action not allowed / revoked / locked", () => {
    authServiceMock.jwtData.set({
      ...authServiceMock.jwtData(),
      rights: []
    } as JwtData);
    table.resetFailCount({ serial: "B", revoked: false, locked: false } as TokenDetails);
    expect(tokenService.resetFailCount).not.toHaveBeenCalled();

    authServiceMock.jwtData.set({
      ...authServiceMock.jwtData(),
      rights: ["reset"]
    } as JwtData);
    table.resetFailCount({ serial: "B", revoked: true, locked: false } as TokenDetails);
    table.resetFailCount({ serial: "B", revoked: false, locked: true } as TokenDetails);
    expect(tokenService.resetFailCount).not.toHaveBeenCalled();
  });

  it("onPageEvent updates page size, index and service's eventPageSize", () => {
    table.onPageEvent({ pageIndex: 2, pageSize: 25, length: 100 } as PageEvent);
    expect(tokenService.eventPageSize()).toBe(25);
    expect(table.pageSize()).toBe(25);
    expect(table.pageIndex()).toBe(2);
  });

  it("onSortEvent sets default when direction empty, else sets provided sort", () => {
    table.onSortEvent({ active: "failcount", direction: "" } as Sort);
    expect(table.sort()).toEqual({ active: "serial", direction: "asc" });

    table.onSortEvent({ active: "description", direction: "desc" } as Sort);
    expect(table.sort()).toEqual({ active: "description", direction: "desc" });
  });

  it("onFilterInput should only update filter if user: and realm: are NOT in the input", () => {
    const inputEvent = { target: { value: "type: hotp" } } as unknown as Event;
    table.onFilterInput(inputEvent);
    expect(tokenService.handleFilterInput).toHaveBeenCalledWith(inputEvent);

    jest.clearAllMocks();
    const inputEventWithUser = { target: { value: "user: admin" } } as unknown as Event;
    table.onFilterInput(inputEventWithUser);
    expect(tokenService.handleFilterInput).not.toHaveBeenCalled();

    const inputEventWithRealm = { target: { value: "realm: default" } } as unknown as Event;
    table.onFilterInput(inputEventWithRealm);
    expect(tokenService.handleFilterInput).not.toHaveBeenCalled();
  });

  it("tokenDataSource/totalLength reflect tokenResource; fall back to empty skeleton when undefined", () => {
    const initial = table.tokenDataSource().data;
    expect(Array.isArray(initial)).toBe(true);
    expect(initial.length).toBe(table.pageSize());

    const tokens = [{ serial: "S-1" }, { serial: "S-2" }] as TokenDetails[];
    tokenService.tokenResourceValue.set({ tokens, count: 2, current: 1 });
    tableFixture.detectChanges();

    expect(table.tokenDataSource().data).toEqual(tokens);
    expect(table.totalLength()).toBe(2);
  });

  it("self-service column keys include revoke/delete depending on permissions", () => {
    authServiceMock.jwtData.set({
      ...authServiceMock.jwtData(),
      rights: ["revoke", "delete"]
    } as JwtData);

    const f1 = TestBed.createComponent(TokenTableSelfServiceComponent);
    const c1 = f1.componentInstance;

    expect(c1.columnKeysSelfService).toEqual(
      expect.arrayContaining([
        "serial",
        "tokentype",
        "description",
        "container_serial",
        "active",
        "failcount",
        "revoke",
        "delete"
      ])
    );

    authServiceMock.jwtData.set({
      ...authServiceMock.jwtData(),
      rights: []
    } as JwtData);

    const f2 = TestBed.createComponent(TokenTableSelfServiceComponent);
    const c2 = f2.componentInstance;

    expect(c2.columnKeysSelfService).toEqual(
      expect.arrayContaining(["serial", "tokentype", "description", "container_serial", "active", "failcount"])
    );
    expect(c2.columnKeysSelfService).not.toEqual(expect.arrayContaining(["revoke", "delete"]));
  });

  it("pageSizeOptions should add custom page size if not included in default options", () => {
    const component = TestBed.createComponent(TokenTableSelfServiceComponent).componentInstance;
    const defaultOptions = [5, 10, 25, 50];
    tableUtilsService.pageSizeOptions.set(defaultOptions);
    expect(component.pageSizeOptions()).toEqual(defaultOptions);

    // Check custom page size is added but does not mutate the options from the service
    const customOptions = [5, 10, 15, 25, 50];
    component.pageSize.set(15);
    expect(component.pageSizeOptions()).toEqual(customOptions);
    expect(tableUtilsService.pageSizeOptions()).toEqual(defaultOptions);

    // custom page size should still be included if selected pageSize changes
    component.pageSize.set(10);
    expect(component.pageSizeOptions()).toEqual(customOptions);
  });

  it("applies and clears a preset filter once the tokens list becomes active", () => {
    const preset = new FilterValue().addEntry("type", "hotp");
    tokenService.presetFilter.set(preset);

    contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS);
    tableFixture.detectChanges();

    expect(tokenService.presetFilter()).toBeNull();
    expect(tokenService.tokenFilter()).toBe(preset);
  });

  it("does not touch the current filter when there is no preset filter to apply", () => {
    const currentFilter = tokenService.tokenFilter();

    contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS);
    tableFixture.detectChanges();

    expect(tokenService.presetFilter()).toBeNull();
    expect(tokenService.tokenFilter()).toBe(currentFilter);
  });

  it("shows a hint while user:/realm: filter syntax is typed but not yet applied", () => {
    authServiceMock.jwtData.set({ ...authServiceMock.jwtData(), rights: ["tokenlist"] } as JwtData);
    tableFixture.detectChanges();

    table.onFilterInput({ target: { value: "user: bob" } } as unknown as Event);
    tableFixture.detectChanges();
    expect(tableFixture.nativeElement.textContent).toContain("Press enter to apply the filter");

    table.onFilterInput({ target: { value: "realm: default" } } as unknown as Event);
    tableFixture.detectChanges();
    expect(tableFixture.nativeElement.textContent).toContain("Press enter to apply the filter");

    table.onFilterInput({ target: { value: "" } } as unknown as Event);
    tableFixture.detectChanges();
    expect(tableFixture.nativeElement.textContent).not.toContain("Press enter to apply the filter");
  });

  it("tokenDataSource/totalLength fall back to empty/zero on resource error", () => {
    tokenService.tokenResource.error.set(new Error("boom"));
    tableFixture.detectChanges();

    expect(table.tokenDataSource().data).toEqual([]);
    expect(table.totalLength()).toBe(0);
  });

  it("totalLength starts at 0 before any value has ever loaded", () => {
    expect(table.totalLength()).toBe(0);
  });

  it("toggleFilter uses the boolean toggler for 'active' and the keyword toggler otherwise", () => {
    const booleanResult = new FilterValue().addEntry("active", "true");
    tableUtilsService.toggleBooleanInFilter.mockReturnValue(booleanResult);
    table.toggleFilter("active");
    expect(tableUtilsService.toggleBooleanInFilter).toHaveBeenCalledWith({
      keyword: "active",
      currentValue: expect.any(FilterValue)
    });
    expect(tokenService.tokenFilter()).toBe(booleanResult);

    const keywordResult = new FilterValue().addEntry("description", "foo");
    tableUtilsService.toggleKeywordInFilter.mockReturnValue(keywordResult);
    table.toggleFilter("description");
    expect(tableUtilsService.toggleKeywordInFilter).toHaveBeenCalledWith({
      keyword: "description",
      currentValue: expect.any(FilterValue)
    });
    expect(tokenService.tokenFilter()).toBe(keywordResult);
  });

  it("toggleFilter adds the default realm when a user filter without a realm is set", () => {
    tableUtilsService.toggleKeywordInFilter.mockReturnValue(new FilterValue().addEntry("user", "bob"));

    table.toggleFilter("user");

    const result = tokenService.tokenFilter();
    expect(result.getValueOfKey("user")).toBe("bob");
    expect(result.getValueOfKey("realm")).toBe("realm1");
  });

  it("toggleFilter does not override an already-present realm on a user filter", () => {
    tableUtilsService.toggleKeywordInFilter.mockReturnValue(
      new FilterValue().addEntry("user", "bob").addEntry("realm", "sub")
    );

    table.toggleFilter("user");

    expect(tokenService.tokenFilter().getValueOfKey("realm")).toBe("sub");
  });

  it("isFilterSelected reports whether a keyword is present in a filter value", () => {
    const filter = new FilterValue().addEntry("active", "true");
    expect(table.isFilterSelected("active", filter)).toBe(true);
    expect(table.isFilterSelected("description", filter)).toBe(false);
  });

  it("getFilterIconName reflects the active/assigned boolean state and generic selection state", () => {
    tokenService.tokenFilter.set(new FilterValue());
    expect(table.getFilterIconName("active")).toBe("filter_alt");

    tokenService.tokenFilter.set(new FilterValue().addEntry("active", "true"));
    expect(table.getFilterIconName("active")).toBe("screen_rotation_alt");

    tokenService.tokenFilter.set(new FilterValue().addEntry("assigned", "false"));
    expect(table.getFilterIconName("assigned")).toBe("filter_alt_off");

    tokenService.tokenFilter.set(new FilterValue());
    expect(table.getFilterIconName("description")).toBe("filter_alt");

    tokenService.tokenFilter.set(new FilterValue().addEntry("description", "foo"));
    expect(table.getFilterIconName("description")).toBe("filter_alt_off");
  });

  it("onKeywordClick toggles the filter, focuses the input, and positions the cursor after 'user:'", async () => {
    authServiceMock.jwtData.set({ ...authServiceMock.jwtData(), rights: ["tokenlist"] } as JwtData);
    tableUtilsService.toggleKeywordInFilter.mockReturnValue(new FilterValue().addEntry("user", "bob"));
    tableFixture.detectChanges();

    const focusSpy = jest.spyOn(table.filterInput.nativeElement, "focus");
    const setSelectionRangeSpy = jest.spyOn(table.filterInput.nativeElement, "setSelectionRange");
    table.filterInput.nativeElement.value = "user: bob ";

    table.onKeywordClick("user");

    expect(tableUtilsService.toggleKeywordInFilter).toHaveBeenCalled();
    expect(focusSpy).toHaveBeenCalled();

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(setSelectionRangeSpy).toHaveBeenCalledWith(6, 6);
  });

  it("onKeywordClick does not schedule cursor positioning for non-user keywords", async () => {
    authServiceMock.jwtData.set({ ...authServiceMock.jwtData(), rights: ["tokenlist"] } as JwtData);
    tableUtilsService.toggleKeywordInFilter.mockReturnValue(new FilterValue().addEntry("description", "foo"));
    tableFixture.detectChanges();

    const setSelectionRangeSpy = jest.spyOn(table.filterInput.nativeElement, "setSelectionRange");

    table.onKeywordClick("description");

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(setSelectionRangeSpy).not.toHaveBeenCalled();
  });

  it("onItemSelected adds or removes a filter entry and focuses the input", () => {
    authServiceMock.jwtData.set({ ...authServiceMock.jwtData(), rights: ["tokenlist"] } as JwtData);
    tableFixture.detectChanges();
    const focusSpy = jest.spyOn(table.filterInput.nativeElement, "focus");

    table.onItemSelected("type", "hotp");
    expect(tokenService.tokenFilter().getValueOfKey("type")).toBe("hotp");
    expect(focusSpy).toHaveBeenCalled();

    table.onItemSelected("type", "");
    expect(tokenService.tokenFilter().hasKey("type")).toBe(false);
  });
});
