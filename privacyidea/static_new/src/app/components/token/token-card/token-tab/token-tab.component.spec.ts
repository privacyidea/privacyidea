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
import { TokenTabComponent } from "./token-tab.component";
import "@angular/localize/init";

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { provideNoopAnimations } from "@angular/platform-browser/animations";

import { signal } from "@angular/core";
import { of, throwError } from "rxjs";

import { MatDialog, MatDialogRef } from "@angular/material/dialog";
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
import { ActivatedRoute, NavigationEnd, Router } from "@angular/router";
import { MockPiResponse } from "../../../../../testing/mock-services";
import { ContentService } from "../../../../services/content/content.service";
import { AuthService } from "../../../../services/auth/auth.service";
import { AuditService } from "../../../../services/audit/audit.service";

describe("TokenTabComponent", () => {
  let component: TokenTabComponent;
  let fixture: ComponentFixture<TokenTabComponent>;
  let tokenService: jest.Mocked<TokenServiceInterface>;
  let dialog: jest.Mocked<MatDialog>;
  let notificationService: jest.Mocked<NotificationServiceInterface>;
  let router: jest.Mocked<Router>;

  beforeEach(async () => {
    const tokenServiceMock = {
      tokenIsActive: signal(true),
      tokenIsRevoked: signal(false),
      tokenSerial: signal("MOCK_SERIAL"),
      tokenSelection: signal<TokenDetails[]>([]),
      tokenDetailResource: { reload: jest.fn() },
      tokenResource: { reload: jest.fn() },
      toggleActive: jest.fn().mockReturnValue(of(null)),
      revokeToken: jest.fn().mockReturnValue(of(null)),
      deleteToken: jest.fn().mockReturnValue(of(null)),
      getTokenDetails: jest.fn().mockReturnValue(of(new MockPiResponse({ detail: {} }))),
      bulkDeleteTokens: jest.fn().mockReturnValue(of({})),
      bulkUnassignTokens: jest.fn().mockReturnValue(of({})),
      assignUser: jest.fn().mockReturnValue(of({})),
      unassignUser: jest.fn().mockReturnValue(of({}))
    };

    const dialogMock = {
      open: jest.fn().mockReturnValue({
        afterClosed: () => of(true)
      } as MatDialogRef<ConfirmationDialogComponent>)
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
      tokenSerial: tokenServiceMock.tokenSerial
    };

    const auditServiceMock = {
      auditFilter: signal({})
    };

    const authServiceMock = {
      hasPermission: jest.fn().mockReturnValue(true),
      tokenEnrollmentAllowed: jest.fn().mockReturnValue(true),
      actionAllowed: jest.fn().mockReturnValue(true),
      actionsAllowed: jest.fn().mockReturnValue(true),
      oneActionAllowed: jest.fn().mockReturnValue(true)
    };

    await TestBed.configureTestingModule({
      imports: [TokenTabComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNoopAnimations(),
        { provide: Router, useValue: routerMock },
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({ id: "123" })
          }
        },
        { provide: TokenService, useValue: tokenServiceMock },
        { provide: MatDialog, useValue: dialogMock },
        { provide: VersioningService, useValue: versioningServiceMock },
        { provide: NotificationService, useValue: notificationServiceMock },
        { provide: ContentService, useValue: contentServiceMock },
        { provide: AuditService, useValue: auditServiceMock },
        { provide: AuthService, useValue: authServiceMock }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenTabComponent);
    component = fixture.componentInstance;
    tokenService = TestBed.inject(TokenService) as unknown as jest.Mocked<TokenServiceInterface>;
    dialog = TestBed.inject(MatDialog) as unknown as jest.Mocked<MatDialog>;
    notificationService = TestBed.inject(NotificationService) as unknown as jest.Mocked<NotificationServiceInterface>;
    router = TestBed.inject(Router) as unknown as jest.Mocked<Router>;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("sets the version on ngOnInit", () => {
    expect(component.version).toBe("1.0.0");
  });

  describe("toggleActive()", () => {
    it("calls service, reloads details", () => {
      component.toggleActive();

      expect(tokenService.toggleActive).toHaveBeenCalledWith("MOCK_SERIAL", true);
      expect(tokenService.tokenDetailResource.reload).toHaveBeenCalled();
    });
  });

  describe("revokeToken()", () => {
    it("opens confirm dialog, revokes, reloads details", () => {
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

  describe("openLostTokenDialog()", () => {
    it("passes the isLost & tokenSerial signals to the dialog", () => {
      component.openLostTokenDialog();

      expect(dialog.open).toHaveBeenCalledWith(expect.any(Function), {
        data: {
          isLost: component.isLost,
          tokenSerial: component.tokenSerial
        }
      });
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

    it("should call batchDeleteTokens and reload on success", () => {
      const response = new MockPiResponse<BulkResult, any>({
        detail: {},
        result: { status: true, value: { count_success: 2, failed: [], unauthorized: [] } }
      });
      tokenService.bulkDeleteTokens.mockReturnValue(of(response));
      component.deleteSelectedTokens();
      expect(tokenService.bulkDeleteTokens).toHaveBeenCalledWith(mockTokens);
      expect(tokenService.tokenResource.reload).toHaveBeenCalled();
      expect(notificationService.openSnackBar).toHaveBeenCalledWith("Successfully deleted 2 tokens.");
    });

    it("should call batchDeleteTokens and reload on success with singular token", () => {
      const singleToken = [{ serial: "TOKEN1" }] as TokenDetails[];
      tokenService.tokenSelection.set(singleToken);
      const response = new MockPiResponse<BulkResult, any>({
        detail: {},
        result: { status: true, value: { count_success: 1, failed: [], unauthorized: [] } }
      });
      tokenService.bulkDeleteTokens.mockReturnValue(of(response));
      component.deleteSelectedTokens();
      expect(tokenService.bulkDeleteTokens).toHaveBeenCalledWith(singleToken);
      expect(tokenService.tokenResource.reload).toHaveBeenCalled();
      expect(notificationService.openSnackBar).toHaveBeenCalledWith("Successfully deleted 1 token.");
    });
    it("should show a notification if some tokens failed or were unauthorized", () => {
      const response = new MockPiResponse<BulkResult, any>({
        detail: {},
        result: { status: true, value: { count_success: 1, failed: ["TOKEN1"], unauthorized: ["TOKEN2"] } }
      });
      tokenService.bulkDeleteTokens.mockReturnValue(of(response));
      component.deleteSelectedTokens();
      expect(notificationService.openSnackBar).toHaveBeenCalledWith(
        "Successfully deleted 1 token.\nThe following tokens failed to delete: TOKEN1\nYou are not authorized to delete the following tokens: TOKEN2"
      );
    });

    it("should handle API errors gracefully", () => {
      tokenService.bulkDeleteTokens.mockReturnValue(throwError(() => new Error("API Error")));
      component.deleteSelectedTokens();
      expect(notificationService.openSnackBar).toHaveBeenCalledWith("An error occurred while deleting tokens.");
    });
  });

  describe("unassignSelectedTokens()", () => {
    const mockTokens = [{ serial: "TOKEN1" }] as TokenDetails[];

    beforeEach(() => {
      tokenService.tokenSelection.set(mockTokens);
    });

    it("should call batchUnassignTokens and reload on success", () => {
      const response = new MockPiResponse<BulkResult, any>({
        detail: {},
        result: { status: true, value: { count_success: 1, failed: [], unauthorized: [] } }
      });
      tokenService.bulkUnassignTokens.mockReturnValue(of(response));
      component.unassignSelectedTokens();
      expect(tokenService.bulkUnassignTokens).toHaveBeenCalledWith(mockTokens);
      expect(tokenService.tokenResource.reload).toHaveBeenCalled();
      expect(notificationService.openSnackBar).toHaveBeenCalledWith("Successfully unassigned 1 token.");
    });
  });

  describe("assignSelectedTokens()", () => {
    it("should do nothing if dialog is cancelled", async () => {
      (dialog.open as jest.Mock).mockReturnValue({ afterClosed: () => of(null) });
      component.assignSelectedTokens();
      jest.advanceTimersByTime(100);
      await Promise.resolve();
      expect(tokenService.assignUser).not.toHaveBeenCalled();
    });

    it("should assign tokens without a user", async () => {
      const tokens = [{ serial: "T1", username: "" }] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);
      (dialog.open as jest.Mock).mockReturnValue({
        afterClosed: () => of({
          username: "new_user",
          realm: "new_realm"
        })
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
        afterClosed: () => of({
          username: "new_user",
          realm: "new_realm"
        })
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
