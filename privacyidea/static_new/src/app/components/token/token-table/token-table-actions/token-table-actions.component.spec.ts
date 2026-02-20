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
import { MatDialog, MatDialogRef } from "@angular/material/dialog";
import { provideNoopAnimations } from "@angular/platform-browser/animations";
import { Router, NavigationEnd, ActivatedRoute } from "@angular/router";
import { of } from "rxjs";
import {
  MockTokenService,
  MockVersioningService,
  MockNotificationService,
  MockContentService,
  MockAuditService,
  MockPiResponse
} from "../../../../../testing/mock-services";
import { MockAuthService } from "../../../../../testing/mock-services/mock-auth-service";
import { AuditService } from "../../../../services/audit/audit.service";
import { AuthService } from "../../../../services/auth/auth.service";
import { ContentService } from "../../../../services/content/content.service";
import {
  NotificationServiceInterface,
  NotificationService
} from "../../../../services/notification/notification.service";
import { TokenService, TokenDetails, BulkResult } from "../../../../services/token/token.service";
import { VersioningService } from "../../../../services/version/version.service";
import { SimpleConfirmationDialogComponent } from "../../../shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { TokenTableActionsComponent } from "./token-table-actions.component";

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
        afterClosed: () => of({ confirmed: true })
      } as unknown as MatDialogRef<SimpleConfirmationDialogComponent>)
    };

    const routerMock = {
      navigateByUrl: jest.fn(),
      events: of(new NavigationEnd(1, "/start", "/start")),
      url: "/start"
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
        { provide: VersioningService, useClass: MockVersioningService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService },
        { provide: AuditService, useClass: MockAuditService },
        { provide: AuthService, useClass: MockAuthService }
      ]
    }).compileComponents();
    fixture = TestBed.createComponent(TokenTableActionsComponent);
    component = fixture.componentInstance;

    tokenService = TestBed.inject(TokenService) as unknown as jest.Mocked<MockTokenService>;
    dialog = TestBed.inject(MatDialog) as unknown as jest.Mocked<MatDialog>;
    notificationService = TestBed.inject(NotificationService) as unknown as jest.Mocked<NotificationServiceInterface>;
    router = TestBed.inject(Router) as unknown as jest.Mocked<Router>;

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("toggleActive()", () => {
    it("calls service, then reloads details", () => {
      component.tokenSerial.set("MOCK_SERIAL");
      jest.spyOn(tokenService, "toggleActive");
      jest.spyOn(tokenService.tokenDetailResource, "reload");
      component.toggleActive();
      expect(tokenService.toggleActive).toHaveBeenCalledWith("MOCK_SERIAL", true);
      expect(tokenService.tokenDetailResource.reload).toHaveBeenCalled();
    });
  });

  describe("revokeToken()", () => {
    it("opens confirm dialog, revokes, reloads details", () => {
      component.tokenSerial.set("MOCK_SERIAL");
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
      component.tokenSerial.set("MOCK_SERIAL");
      component.deleteToken();

      expect(dialog.open).toHaveBeenCalled();
      expect(tokenService.deleteToken).toHaveBeenCalledWith("MOCK_SERIAL");
      expect(router.navigateByUrl).toHaveBeenCalledWith("/tokens");
    });
  });

  describe("deleteSelectedTokens()", () => {
    it("should call bulkDeleteWithConfirmDialog with the selected token serials", () => {
      const mockTokens = [{ serial: "TOKEN1" }, { serial: "TOKEN2" }] as TokenDetails[];
      tokenService.tokenSelection.set(mockTokens);
      fixture.detectChanges();

      component.deleteSelectedTokens();

      expect(tokenService.bulkDeleteWithConfirmDialog).toHaveBeenCalledWith(["TOKEN1", "TOKEN2"], expect.any(Function));
    });
  });

  describe("unassignSelectedTokens()", () => {
    const mockTokens = [{ serial: "TOKEN1" }] as TokenDetails[];

    beforeEach(() => {
      tokenService.tokenSelection.set(mockTokens);
    });

    it("should call bulkUnassignTokens and reload when dialog result is true", () => {
      const bulkUnassignResponse = new MockPiResponse<BulkResult, any>({
        detail: {},
        result: {
          status: true,
          value: { count_success: 1, failed: [], unauthorized: [] }
        }
      });

      const bulkUnassignSpy = jest.spyOn(tokenService, "bulkUnassignTokens").mockReturnValue(of(bulkUnassignResponse));

      const reloadSpy = jest.spyOn(tokenService.tokenResource, "reload");

      const dialogSpy = jest.spyOn(dialog, "open").mockReturnValue({
        afterClosed: () => of({ confirmed: true })
      } as any);

      component.tokenSelection.set(mockTokens);
      component.unassignSelectedTokens();

      expect(dialogSpy).toHaveBeenCalledWith(SimpleConfirmationDialogComponent, {
        data: {
          confirmAction: { label: "Unassign", type: "destruct", value: true },
          itemType: "token",
          items: ["TOKEN1"],
          title: "Unassign Selected Tokens"
        },
        disableClose: false,
        hasBackdrop: true
      });
      expect(bulkUnassignSpy).toHaveBeenCalledWith(mockTokens);
      expect(notificationService.openSnackBar).toHaveBeenCalledWith("Successfully unassigned 1 token.");
      expect(reloadSpy).toHaveBeenCalled();
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
