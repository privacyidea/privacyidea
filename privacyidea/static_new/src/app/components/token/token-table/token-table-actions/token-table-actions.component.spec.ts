/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import "@angular/localize/init";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { TokenTableActionsComponent } from "./token-table-actions.component";

import { signal } from "@angular/core";
import { of, throwError } from "rxjs";

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { provideNoopAnimations } from "@angular/platform-browser/animations";

import { MatDialog, MatDialogRef } from "@angular/material/dialog";
import { ActivatedRoute, NavigationEnd, Router } from "@angular/router";

import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../services/notification/notification.service";
import {
  TokenService,
  TokenServiceInterface
} from "../../../../services/token/token.service";
import { VersioningService } from "../../../../services/version/version.service";
import { ContentService } from "../../../../services/content/content.service";
import { AuthService } from "../../../../services/auth/auth.service";
import { AuditService } from "../../../../services/audit/audit.service";
import { ConfirmationDialogComponent } from "../../../shared/confirmation-dialog/confirmation-dialog.component";

describe("TokenTableActionsComponent", () => {
  let component: TokenTableActionsComponent;
  let fixture: ComponentFixture<TokenTableActionsComponent>;
  let tokenService: jest.Mocked<TokenServiceInterface>;
  let dialog: jest.Mocked<MatDialog>;
  let notificationService: jest.Mocked<NotificationServiceInterface>;
  let router: jest.Mocked<Router>;

  class MockTokenService implements Partial<TokenServiceInterface> {
    tokenIsActive = signal(true);
    tokenIsRevoked = signal(false);
    tokenSerial = signal("MOCK_SERIAL");
    tokenSelection = signal<any[]>([]);
    tokenDetailResource = { reload: jest.fn() } as any;
    tokenResource = { reload: jest.fn() } as any;

    toggleActive = jest.fn().mockReturnValue(of({}));
    revokeToken = jest.fn().mockReturnValue(of({}));
    getTokenDetails = jest.fn().mockReturnValue(of({}));
    deleteToken = jest.fn().mockReturnValue(of({}));
    bulkDeleteTokens = jest.fn().mockReturnValue(of({}));
    bulkUnassignTokens = jest.fn().mockReturnValue(of({}));
    unassignUser = jest.fn().mockReturnValue(of({}));
    assignUser = jest.fn().mockReturnValue(of({}));
  }

  beforeEach(async () => {
    const dialogMock: jest.Mocked<MatDialog> = {
      open: jest.fn().mockReturnValue({
        afterClosed: () => of(true)
      } as unknown as MatDialogRef<ConfirmationDialogComponent>)
    } as any;

    const versioningServiceMock = {
      getVersion: jest.fn().mockReturnValue("1.0.0"),
      openDocumentation: jest.fn()
    };

    const notificationServiceMock: jest.Mocked<NotificationServiceInterface> = {
      openSnackBar: jest.fn()
    } as any;

    const routerMock: jest.Mocked<Router> = {
      navigateByUrl: jest.fn().mockReturnValue(Promise.resolve(true)),
      events: of(new NavigationEnd(1, "/start", "/start")) as any,
      url: "/start"
    } as any;

    const contentServiceMock = {
      routeUrl: signal("/tokens"),
      tokenSerial: "MOCK_SERIAL"
    };

    const auditServiceMock = {
      auditFilter: signal({})
    };

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
        {
          provide: ActivatedRoute,
          useValue: { params: of({ id: "123" }) }
        },
        { provide: TokenService, useClass: MockTokenService },
        { provide: MatDialog, useValue: dialogMock },
        { provide: VersioningService, useValue: versioningServiceMock },
        { provide: NotificationService, useValue: notificationServiceMock },
        { provide: ContentService, useValue: contentServiceMock },
        { provide: AuditService, useValue: auditServiceMock },
        { provide: AuthService, useValue: authServiceMock }
      ]
    })
      // Avoid needing the external HTML/SCSS in tests
      .overrideComponent(TokenTableActionsComponent, { set: { template: "" } })
      .compileComponents();

    fixture = TestBed.createComponent(TokenTableActionsComponent);
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

  describe("toggleActive()", () => {
    it("calls service and reloads details", () => {
      jest.spyOn(tokenService, "toggleActive");
      const reloadSpy = jest.spyOn((tokenService as any).tokenDetailResource, "reload");

      component.toggleActive();

      expect(tokenService.toggleActive).toHaveBeenCalledWith("MOCK_SERIAL", true);
      expect(reloadSpy).toHaveBeenCalled();
    });
  });

  describe("revokeToken()", () => {
    it("opens confirmation, revokes, refreshes details", () => {
      const revokeSpy = jest.spyOn(tokenService, "revokeToken");
      const detailsSpy = jest.spyOn(tokenService, "getTokenDetails");
      const reloadSpy = jest.spyOn((tokenService as any).tokenDetailResource, "reload");

      component.revokeToken();

      expect(dialog.open).toHaveBeenCalled(); // with ConfirmationDialogComponent
      expect(revokeSpy).toHaveBeenCalledWith("MOCK_SERIAL");
      expect(detailsSpy).toHaveBeenCalledWith("MOCK_SERIAL");
      expect(reloadSpy).toHaveBeenCalled();
    });
  });

  describe("deleteToken()", () => {
    it("opens confirmation, deletes, navigates and clears serial", () => {
      component.deleteToken();

      expect(dialog.open).toHaveBeenCalled();
      expect(tokenService.deleteToken).toHaveBeenCalledWith("MOCK_SERIAL");
      expect(router.navigateByUrl).toHaveBeenCalledWith(component.ROUTE_PATHS.TOKENS);
      expect((tokenService as any).tokenSerial()).toBe(""); // cleared
    });
  });

  describe("openLostTokenDialog()", () => {
    it("passes signals to dialog", () => {
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
    const selected = [{ serial: "T1" }, { serial: "T2" }] as any[];

    beforeEach(() => {
      (tokenService as any).tokenSelection.set(selected);
    });

    it("does nothing when dialog is cancelled", () => {
      (dialog.open as jest.Mock).mockReturnValue({ afterClosed: () => of(false) } as any);
      component.deleteSelectedTokens();
      expect(tokenService.bulkDeleteTokens).not.toHaveBeenCalled();
    });

    it("deletes and reloads on success (plural)", () => {
      tokenService.bulkDeleteTokens = jest.fn().mockReturnValue(
        of({ result: { value: { count_success: 2, failed: [], unauthorized: [] } } })
      ) as any;

      component.deleteSelectedTokens();

      expect(tokenService.bulkDeleteTokens).toHaveBeenCalledWith(selected);
      expect((tokenService as any).tokenResource.reload).toHaveBeenCalled();
      expect(notificationService.openSnackBar).toHaveBeenCalledWith("Successfully deleted 2 tokens.");
    });

    it("deletes and reloads on success (singular)", () => {
      (tokenService as any).tokenSelection.set([{ serial: "ONLY" }]);
      tokenService.bulkDeleteTokens = jest.fn().mockReturnValue(
        of({ result: { value: { count_success: 1, failed: [], unauthorized: [] } } })
      ) as any;

      component.deleteSelectedTokens();

      expect(tokenService.bulkDeleteTokens).toHaveBeenCalledWith([{ serial: "ONLY" }]);
      expect((tokenService as any).tokenResource.reload).toHaveBeenCalled();
      expect(notificationService.openSnackBar).toHaveBeenCalledWith("Successfully deleted 1 token.");
    });

    it("shows combined message for failed and unauthorized", () => {
      tokenService.bulkDeleteTokens = jest.fn().mockReturnValue(
        of({ result: { value: { count_success: 1, failed: ["T1"], unauthorized: ["T2"] } } })
      ) as any;

      component.deleteSelectedTokens();

      expect(notificationService.openSnackBar).toHaveBeenCalledWith(
        "Successfully deleted 1 token.\nThe following tokens failed to delete: T1\nYou are not authorized to delete the following tokens: T2"
      );
    });

    it("handles API errors with default message", () => {
      tokenService.bulkDeleteTokens = jest.fn().mockReturnValue(throwError(() => new Error("boom"))) as any;

      component.deleteSelectedTokens();

      expect(notificationService.openSnackBar).toHaveBeenCalledWith(
        "An error occurred while deleting tokens."
      );
    });

    it("handles API errors with server message", () => {
      tokenService.bulkDeleteTokens = jest.fn().mockReturnValue(
        throwError(() => ({ error: { result: { error: { message: "Nope." } } } }))
      ) as any;

      component.deleteSelectedTokens();

      expect(notificationService.openSnackBar).toHaveBeenCalledWith("Nope.");
    });
  });

  describe("unassignSelectedTokens()", () => {
    const selected = [{ serial: "T1" }] as any[];

    beforeEach(() => {
      (tokenService as any).tokenSelection.set(selected);
    });

    it("opens confirmation, unassigns, reloads and notifies", () => {
      tokenService.bulkUnassignTokens = jest.fn().mockReturnValue(
        of({ result: { value: { count_success: 1, failed: [], unauthorized: [] } } })
      ) as any;

      component.unassignSelectedTokens();

      expect(tokenService.bulkUnassignTokens).toHaveBeenCalledWith(selected);
      expect((tokenService as any).tokenResource.reload).toHaveBeenCalled();
      expect(notificationService.openSnackBar).toHaveBeenCalledWith(
        "Successfully unassigned 1 token."
      );
    });
  });

  describe("assignSelectedTokens()", () => {
    it("does nothing if dialog is cancelled", () => {
      (dialog.open as jest.Mock).mockReturnValue({ afterClosed: () => of(null) } as any);

      component.assignSelectedTokens();

      expect(tokenService.assignUser).not.toHaveBeenCalled();
      expect(tokenService.unassignUser).not.toHaveBeenCalled();
    });

    it("assigns tokens without an existing user", () => {
      (tokenService as any).tokenSelection.set([{ serial: "T1", username: "" }]);
      (dialog.open as jest.Mock).mockReturnValue({
        afterClosed: () => of({ username: "new_user", realm: "new_realm" })
      } as any);

      component.assignSelectedTokens();

      expect(tokenService.unassignUser).not.toHaveBeenCalled();
      expect(tokenService.assignUser).toHaveBeenCalledWith({
        tokenSerial: "T1",
        username: "new_user",
        realm: "new_realm"
      });
      expect((tokenService as any).tokenResource.reload).toHaveBeenCalled();
    });

    it("unassigns first, then assigns when token already has a user", () => {
      (tokenService as any).tokenSelection.set([{ serial: "T1", username: "old_user" }]);
      (dialog.open as jest.Mock).mockReturnValue({
        afterClosed: () => of({ username: "new_user", realm: "new_realm" })
      } as any);

      component.assignSelectedTokens();

      expect(tokenService.unassignUser).toHaveBeenCalledWith("T1");
      expect(tokenService.assignUser).toHaveBeenCalledWith({
        tokenSerial: "T1",
        username: "new_user",
        realm: "new_realm"
      });
      expect((tokenService as any).tokenResource.reload).toHaveBeenCalled();
    });

    it("shows an error snack when assignment fails", () => {
      (tokenService as any).tokenSelection.set([{ serial: "T1", username: "" }]);
      (dialog.open as jest.Mock).mockReturnValue({
        afterClosed: () => of({ username: "new_user", realm: "new_realm" })
      } as any);

      tokenService.assignUser = jest.fn().mockReturnValue(
        throwError(() => ({ error: { result: { error: { message: "Assign failed" } } } }))
      ) as any;

      component.assignSelectedTokens();

      expect(notificationService.openSnackBar).toHaveBeenCalledWith("Assign failed");
      expect((tokenService as any).tokenResource.reload).not.toHaveBeenCalled();
    });
  });
});
