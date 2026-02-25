/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { UserResolversComponent } from "./user-resolvers.component";
import { Resolver, ResolverService } from "../../../services/resolver/resolver.service";
import { TableUtilsService } from "../../../services/table-utils/table-utils.service";
import { NotificationService } from "../../../services/notification/notification.service";
import { AuthService } from "../../../services/auth/auth.service";
import { MatDialog } from "@angular/material/dialog";
import { of } from "rxjs";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ActivatedRoute, Router } from "@angular/router";
import { MockResolverService } from "../../../../testing/mock-services/mock-resolver-service";
import { MockNotificationService, MockTableUtilsService } from "../../../../testing/mock-services";
import { MockAuthService } from "../../../../testing/mock-services/mock-auth-service";

class LocalMockMatDialog {
  result$ = of(true);
  open = jest.fn(() => ({
    afterClosed: () => this.result$
  }));
}

describe("UserSourcesComponent", () => {
  let component: UserResolversComponent;
  let fixture: ComponentFixture<UserResolversComponent>;
  let resolverService: MockResolverService;
  let notificationService: MockNotificationService;
  let dialog: LocalMockMatDialog;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserResolversComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ResolverService, useClass: MockResolverService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: MatDialog, useClass: LocalMockMatDialog },
        {
          provide: Router,
          useValue: {
            navigate: jest.fn()
          }
        },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { paramMap: { get: () => null } }
          }
        }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(UserResolversComponent);
    component = fixture.componentInstance;
    resolverService = TestBed.inject(ResolverService) as unknown as MockResolverService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    dialog = TestBed.inject(MatDialog) as unknown as LocalMockMatDialog;
    router = TestBed.inject(Router);

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should have columns defined", () => {
    expect(component.columnKeys).toContain("resolvername");
    expect(component.columnKeys).toContain("type");
    expect(component.columnKeys).not.toContain("actions");
  });

  it("should filter resolvers", () => {
    const resolvers = [
      { resolvername: "admin", type: "passwdresolver", censor_keys: [], data: {} },
      { resolvername: "sql-res", type: "sqlresolver", censor_keys: [], data: {} }
    ] as Resolver[];
    resolverService.setResolvers(resolvers);
    fixture.detectChanges();

    component.onFilterInput("admin");
    expect(component.resolversDataSource().filter).toBe("admin");
    expect(component.resolversDataSource().filteredData.length).toBe(1);
    expect(component.resolversDataSource().filteredData[0].resolvername).toBe("admin");

    component.resetFilter();
    expect(component.filterString()).toBe("");
    expect(component.resolversDataSource().filter).toBe("");
    expect(component.resolversDataSource().filteredData.length).toBe(2);
  });

  it("filterPredicate should match name or type", () => {
    const resolvers = [{ resolvername: "admin", type: "passwdresolver", censor_keys: [], data: {} }] as Resolver[];
    resolverService.setResolvers(resolvers);
    fixture.detectChanges();

    const ds = component.resolversDataSource();
    expect(ds.filterPredicate(resolvers[0] as any, "admin")).toBeTruthy();
    expect(ds.filterPredicate(resolvers[0] as any, "passwd")).toBeTruthy();
    expect(ds.filterPredicate(resolvers[0] as any, "nomatch")).toBeFalsy();
    expect(ds.filterPredicate(resolvers[0] as any, "  ")).toBeTruthy();
  });

  it("onEditResolver should open dialog", () => {
    const resolver = { resolvername: "res1", type: "sqlresolver", censor_keys: [], data: {} } as Resolver;
    component.onEditResolver(resolver);

    expect(dialog.open).toHaveBeenCalledWith(
      expect.any(Function),
      expect.objectContaining({
        data: { resolver },
        height: "auto",
        maxHeight: "100vh",
        maxWidth: "100vw",
        width: "auto"
      })
    );
  });

  it("onNewResolver should open dialog", () => {
    component.onNewResolver();

    expect(dialog.open).toHaveBeenCalledWith(
      expect.any(Function),
      expect.objectContaining({
        data: { resolver: undefined },
        height: "auto",
        maxHeight: "100vh",
        maxWidth: "100vw",
        width: "auto"
      })
    );
  });

  it("onDeleteResolver should delete after confirmation", () => {
    dialog.result$ = of(true);
    const resolver = { resolvername: "res1", type: "passwdresolver", censor_keys: [], data: {} } as Resolver;

    component.onDeleteResolver(resolver);

    expect(dialog.open).toHaveBeenCalled();
    expect(resolverService.deleteResolver).toHaveBeenCalledWith("res1");
    expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining("deleted"));
  });

  it("onDeleteResolver should not delete if cancelled", () => {
    dialog.result$ = of(false);
    const resolver = { resolvername: "res1", type: "passwdresolver", censor_keys: [], data: {} } as Resolver;

    component.onDeleteResolver(resolver);

    expect(dialog.open).toHaveBeenCalled();
    expect(resolverService.deleteResolver).not.toHaveBeenCalled();
  });

  it("onDeleteResolver should show error if delete fails", () => {
    dialog.result$ = of(true);
    const resolver = { resolvername: "res1", type: "passwdresolver", censor_keys: [], data: {} } as Resolver;
    resolverService.deleteResolver.mockReturnValue({
      subscribe: (obs: any) => obs.error({ message: "Delete failed" })
    } as any);

    component.onDeleteResolver(resolver);

    expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining("Delete failed"));
  });

  it("onDeleteResolver should show error message from response if delete fails", () => {
    dialog.result$ = of(true);
    const resolver = { resolvername: "res1", type: "passwdresolver", censor_keys: [], data: {} } as Resolver;
    const errorResponse = {
      error: {
        result: {
          error: {
            message: "Server error message"
          }
        }
      }
    };
    resolverService.deleteResolver.mockReturnValue({
      subscribe: (obs: any) => obs.error(errorResponse)
    } as any);

    component.onDeleteResolver(resolver);

    expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining("Server error message"));
  });
});
