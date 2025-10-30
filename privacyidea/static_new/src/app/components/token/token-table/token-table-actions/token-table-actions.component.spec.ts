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
 * License along with this program. If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { ComponentFixture, TestBed } from "@angular/core/testing";
import "@angular/localize/init";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { provideNoopAnimations } from "@angular/platform-browser/animations";
import { of, throwError } from "rxjs";
import { signal } from "@angular/core";
import { MatDialog, MatDialogRef } from "@angular/material/dialog";
import { ActivatedRoute, NavigationEnd, Router } from "@angular/router";

import { TokenTableActionsComponent } from "./token-table-actions.component";

import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../services/notification/notification.service";

import {
  BulkResult,
  TokenDetails,
  TokenService,
  TokenServiceInterface
} from "../../../../services/token/token.service";

import { VersioningService } from "../../../../services/version/version.service";
import { ConfirmationDialogComponent } from "../../../shared/confirmation-dialog/confirmation-dialog.component";
import { ContentService } from "../../../../services/content/content.service";
import { AuthService } from "../../../../services/auth/auth.service";
import { AuditService } from "../../../../services/audit/audit.service";

import {
  MockPiResponse,
  MockTokenService
} from "../../../../../testing/mock-services";

describe("TokenTableActionsComponent", () => {
  let component: TokenTableActionsComponent;
  let fixture: ComponentFixture<TokenTableActionsComponent>;

  let tokenService: jest.Mocked<MockTokenService>;
  let dialog: jest.Mocked<MatDialog>;
  let notificationService: jest.Mocked<NotificationServiceInterface>;
  let router: jest.Mocked<Router>;

  beforeEach(async () => {
    const dialogMock = {
      open: jest.fn().mockReturnValue({
        afterClosed: () => of(true)
      } as unknown as MatDialogRef<ConfirmationDialogComponent>)
    };

    const versioningServiceMock = {
      getVersion: jest.fn().mockReturnValue("1.0.0"),
      openDocumentation: jest.fn()
    };

    const notificationServiceMock = {
      openSnackBar: jest.fn()
    };

    const routerMock = {
      navigateByUrl: jest.fn(),
      events: of(new NavigationEnd(1, "/start", "/start")),
      url: "/start"
    };

    const contentServiceMock = {
      routeUrl: signal("/tokens"),
      tokenSerial: "MOCK_SERIAL"
    };

    const auditServiceMock = { auditFilter: signal({}) };

    const authServiceMock = {
      hasPermission: jest.fn().mockReturnValue(true),
      tokenEnrollmentAllowed: jest.fn().mockReturnValue(true),
      actionAllowed: jest.fn().mockReturnValue(true),
      actionsAllowed: jest.fn().mockReturnValue(true),
      oneActionAllowed: jest.fn().mockReturnValue(true),
      getHeaders: jest.fn().mockReturnValue({})
    };

    await TestBed.configureTestingModule({
      imports: [TokenTableActionsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNoopAnimations(),
        { provide: Router, useValue: routerMock },
        { provide: ActivatedRoute, useValue: { params: of({ id: "123" }) } },
        { provide: TokenService, useClass: MockTokenService },
        { provide: MatDialog, useValue: dialogMock },
        { provide: VersioningService, useValue: versioningServiceMock },
        { provide: NotificationService, useValue: notificationServiceMock },
        { provide: ContentService, useValue: contentServiceMock },
        { provide: AuditService, useValue: auditServiceMock },
        { provide: AuthService, useValue: authServiceMock }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenTableActionsComponent);
    component = fixture.componentInstance;

    tokenService = TestBed.inject(TokenService) as unknown as jest.Mocked<MockTokenService>;
    dialog = TestBed.inject(MatDialog) as unknown as jest.Mocked<MatDialog>;
    notificationService = TestBed.inject(
      NotificationService
    ) as unknown as jest.Mocked<NotificationServiceInterface>;
    router = TestBed.inject(Router) as unknown as jest.Mocked<Router>;

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("toggleActive()", () => {
    it("calls service, then reloads details", () => {
      jest.spyOn(tokenService, "toggleActive");
      jest.spyOn(tokenService.tokenDetailResource, "reload");
      component.toggleActive();
      expect(tokenService.toggleActive).toHaveBeenCalledWith("MOCK_SERIAL", true);
      expect(tokenService.tokenDetailResource.reload).toHaveBeenCalled();
    });
  });

  describe("revokeToken()", () => {
    it("opens confirm dialog, revokes, reloads details", () => {
      jest.spyOn(tokenService, "revokeToken");
      jest.spyOn(tokenService, "getTokenDetails");
      jest.spyOn(tokenService.tokenDetailResource, "reload");

      component.revokeToken();

      expect(dialog.open).toHaveBeenCalled();
      expect(tokenService.revokeToken).toHaveBeenCalledWith("MOCK_SERIAL");
      expect(tokenService.getTokenDetails).toHaveBeenCalledWith("MOCK_SERIAL");
      expect(tokenService.tokenDetailResource.reload).toHaveBeenCalled();
    });
  });

  describe("deleteToken()", () => {
    it("opens confirm dialog, deletes and navigates", () => {
      component.deleteToken();

      expect(dialog.open).toHaveBeenCalled();
      expect(tokenService.deleteToken).toHaveBeenCalledWith("MOCK_SERIAL");
      expect(router.navigateByUrl).toHaveBeenCalledWith("/tokens");
    });
  });

  describe("deleteSelectedTokens()", () => {
    const mockTokens = [{ serial: "TOKEN1" }, { serial: "TOKEN2" }] as TokenDetails[];

    beforeEach(() => {
      tokenService.tokenSelection.set(mockTokens);
    });

    it("should do nothing if dialog is cancelled", () => {
      (dialog.open as jest.Mock).mockReturnValue({ afterClosed: () => of(false) });
      component.deleteSelectedTokens();
      expect(tokenService.bulkDeleteTokens).not.toHaveBeenCalled();
    });

    it("should call bulkDeleteTokens and reload on success", () => {
      const response = new MockPiResponse<BulkResult, any>({
        detail: {},
        result: {
          status: true,
          value: { count_success: 2, failed: [], unauthorized: [] }
        }
      });
      tokenService.bulkDeleteTokens.mockReturnValue(of(response));

      component.deleteSelectedTokens();

      expect(tokenService.bulkDeleteTokens).toHaveBeenCalledWith(
        mockTokens.map(t => t.serial)
      );
      expect(tokenService.tokenResource.reload).toHaveBeenCalled();
      expect(notificationService.openSnackBar).toHaveBeenCalledWith(
        "Successfully deleted 2 tokens."
      );
    });

    it("should call bulkDeleteTokens and reload on success with singular token", () => {
      const single = [{ serial: "TOKEN1" }] as TokenDetails[];
      tokenService.tokenSelection.set(single);

      const response = new MockPiResponse<BulkResult, any>({
        detail: {},
        result: {
          status: true,
          value: { count_success: 1, failed: [], unauthorized: [] }
        }
      });
      tokenService.bulkDeleteTokens.mockReturnValue(of(response));

      component.deleteSelectedTokens();

      expect(tokenService.bulkDeleteTokens).toHaveBeenCalledWith(["TOKEN1"]);
      expect(tokenService.tokenResource.reload).toHaveBeenCalled();
      expect(notificationService.openSnackBar).toHaveBeenCalledWith(
        "Successfully deleted 1 token."
      );
    });

    it("should show a notification if some tokens failed or were unauthorized", () => {
      const response = new MockPiResponse<BulkResult, any>({
        detail: {},
        result: {
          status: true,
          value: {
            count_success: 1,
            failed: ["TOKEN1"],
            unauthorized: ["TOKEN2"]
          }
        }
      });
      tokenService.bulkDeleteTokens.mockReturnValue(of(response));

      component.deleteSelectedTokens();

      expect(notificationService.openSnackBar).toHaveBeenCalledWith(
        "Successfully deleted 1 token.\nThe following tokens failed to delete: TOKEN1\nYou are not authorized to delete the following tokens: TOKEN2"
      );
    });

    it("should handle API errors gracefully", () => {
      tokenService.bulkDeleteTokens.mockReturnValue(
        throwError(() => new Error("API Error"))
      );

      component.deleteSelectedTokens();

      expect(notificationService.openSnackBar).toHaveBeenCalledWith(
        "An error occurred while deleting tokens."
      );
    });
  });

  describe("unassignSelectedTokens()", () => {
    const mockTokens = [{ serial: "TOKEN1" }] as TokenDetails[];

    beforeEach(() => {
      tokenService.tokenSelection.set(mockTokens);
    });

    it("should call bulkUnassignTokens and reload on success", () => {
      const response = new MockPiResponse<BulkResult, any>({
        detail: {},
        result: {
          status: true,
          value: { count_success: 1, failed: [], unauthorized: [] }
        }
      });

      jest.spyOn(tokenService, "bulkUnassignTokens").mockReturnValue(of(response));

      component.unassignSelectedTokens();

      expect(tokenService.bulkUnassignTokens).toHaveBeenCalledWith(mockTokens);
      expect(tokenService.tokenResource.reload).toHaveBeenCalled();
      expect(notificationService.openSnackBar).toHaveBeenCalledWith(
        "Successfully unassigned 1 token."
      );
    });
  });

  describe("assignSelectedTokens()", () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });
    afterEach(() => {
      jest.useRealTimers();
    });

    it("should do nothing if dialog is cancelled", async () => {
      (dialog.open as jest.Mock).mockReturnValue({ afterClosed: () => of(null) });

      component.assignSelectedTokens();

      jest.advanceTimersByTime(100);
      await Promise.resolve();

      expect(tokenService.assignUser).not.toHaveBeenCalled();
      expect(tokenService.unassignUser).not.toHaveBeenCalled();
    });

    it("should assign tokens without an existing user", async () => {
      const tokens = [{ serial: "T1", username: "" }] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);

      (dialog.open as jest.Mock).mockReturnValue({
        afterClosed: () => of({ username: "new_user", realm: "new_realm" })
      });

      component.assignSelectedTokens();

      jest.advanceTimersByTime(100);
      await Promise.resolve();

      expect(tokenService.unassignUser).not.toHaveBeenCalled();
      expect(tokenService.assignUser).toHaveBeenCalledWith({
        tokenSerial: "T1",
        username: "new_user",
        realm: "new_realm"
      });
      expect(tokenService.tokenResource.reload).toHaveBeenCalled();
    });

    it("should unassign and then re-assign tokens that already have a user", async () => {
      const tokens = [{ serial: "T1", username: "old_user" }] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);

      (dialog.open as jest.Mock).mockReturnValue({
        afterClosed: () => of({ username: "new_user", realm: "new_realm" })
      });

      component.assignSelectedTokens();

      jest.advanceTimersByTime(100);
      await Promise.resolve();

      expect(tokenService.unassignUser).toHaveBeenCalledWith("T1");
      expect(tokenService.assignUser).toHaveBeenCalledWith({
        tokenSerial: "T1",
        username: "new_user",
        realm: "new_realm"
      });
      expect(tokenService.tokenResource.reload).toHaveBeenCalled();
    });
  });
});
