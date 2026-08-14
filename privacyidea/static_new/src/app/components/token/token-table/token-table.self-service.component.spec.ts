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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatDialog } from "@angular/material/dialog";
import { provideRouter } from "@angular/router";
import { AuditService } from "@services/audit/audit.service";
import { AuthService } from "@services/auth/auth.service";
import { ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { DocumentationService } from "@services/documentation/documentation.service";
import { RealmService } from "@services/realm/realm.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { TokenDetails, Tokens, TokenService } from "@services/token/token.service";
import {
  MatDialogMock,
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
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { expectsTableStateGating } from "@testing/table-state-gating";
import { of } from "rxjs";
import { TokenTableSelfServiceComponent } from "./token-table.self-service.component";

describe("TokenTableSelfServiceComponent", () => {
  let fixture: ComponentFixture<TokenTableSelfServiceComponent>;
  let component: TokenTableSelfServiceComponent;

  let tokenServiceMock: MockTokenService;
  let authServiceMock: MockAuthService;
  let dialogServiceMock: MockDialogService;

  const closesDialogWith = (result: unknown): void => {
    dialogServiceMock.openDialog.mockReturnValue({
      afterClosed: () => of(result)
    } as ReturnType<DialogService["openDialog"]>);
  };

  beforeEach(async () => {
    TestBed.resetTestingModule();

    await TestBed.configureTestingModule({
      imports: [TokenTableSelfServiceComponent],
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

    tokenServiceMock = TestBed.inject(TokenService) as unknown as MockTokenService;
    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;

    fixture = TestBed.createComponent(TokenTableSelfServiceComponent);
    component = fixture.componentInstance;
  });

  afterEach(() => jest.clearAllMocks());

  it("lists the user's tokens without requiring the admin-only tokenlist right", () => {
    // tokenlist exists in the admin policy scope only, so gating the rows on it would leave every
    // self-service user with an empty table under a paginator showing the real count.
    authServiceMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: [], role: "user" });
    (authServiceMock.role as unknown as { set: (r: string) => void }).set("user");
    tokenServiceMock.tokenResourceValue.set(
      MockPiResponse.fromValue<Tokens>({
        count: 1,
        current: 1,
        tokens: [{ serial: "T-SELF" }] as TokenDetails[]
      }).result!.value!
    );

    expect(component.tokenDataSource().data.map((token) => token.serial)).toEqual(["T-SELF"]);
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("gates the table on its row count and filter, with no read right of its own", () => {
    // Self service lists the user's own tokens, so the state carries no `allowed` callback.
    expectsTableStateGating({ state: component.tableState });
  });

  describe("columns", () => {
    const rights = (...names: string[]): void => {
      authServiceMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: names });
    };

    it("always offers the token's own details", () => {
      rights();
      expect(component.columnKeysMapSelfService().map((column) => column.key)).toEqual([
        "serial",
        "tokentype",
        "description",
        "container_serial",
        "active",
        "failcount"
      ]);
    });

    it("adds the revoke and delete columns only for the rights that allow them", () => {
      rights("revoke");
      expect(component.columnKeysMapSelfService().map((column) => column.key)).toContain("revoke");
      expect(component.columnKeysMapSelfService().map((column) => column.key)).not.toContain("delete");

      rights("delete");
      expect(component.columnKeysMapSelfService().map((column) => column.key)).toContain("delete");
      expect(component.columnKeysMapSelfService().map((column) => column.key)).not.toContain("revoke");

      rights("revoke", "delete");
      const keys = component.columnKeysMapSelfService().map((column) => column.key);
      expect(keys).toContain("revoke");
      expect(keys).toContain("delete");
    });
  });

  describe("revokeToken", () => {
    it("revokes the token and reloads once the user confirms", () => {
      closesDialogWith(true);

      component.revokeToken("T-1");

      expect(tokenServiceMock.revokeToken).toHaveBeenCalledWith("T-1");
      expect(tokenServiceMock.tokenResource.reload).toHaveBeenCalled();
    });

    it("leaves the token alone when the user cancels", () => {
      closesDialogWith(false);

      component.revokeToken("T-1");

      expect(tokenServiceMock.revokeToken).not.toHaveBeenCalled();
      expect(tokenServiceMock.tokenResource.reload).not.toHaveBeenCalled();
    });
  });

  describe("deleteToken", () => {
    it("deletes the token and reloads once the user confirms", () => {
      closesDialogWith(true);

      component.deleteToken("T-2");

      expect(tokenServiceMock.deleteToken).toHaveBeenCalledWith("T-2");
      expect(tokenServiceMock.tokenResource.reload).toHaveBeenCalled();
    });

    it("leaves the token alone when the user cancels", () => {
      closesDialogWith(false);

      component.deleteToken("T-2");

      expect(tokenServiceMock.deleteToken).not.toHaveBeenCalled();
      expect(tokenServiceMock.tokenResource.reload).not.toHaveBeenCalled();
    });
  });
});
