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
import { ActivatedRoute, Router } from "@angular/router";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { AuditService } from "@services/audit/audit.service";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { BulkResult, TokenDetails, TokenService } from "@services/token/token.service";
import { VersioningService } from "@services/version/version.service";
import {
  MockAuditService,
  MockAuthService,
  MockContentService,
  MockDialogService,
  MockDocumentationService,
  MockNotificationService,
  MockPiResponse,
  MockRouter,
  MockTableUtilsService,
  MockTokenService,
  MockVersioningService
} from "@testing/mock-services";
import { of, throwError } from "rxjs";
import { TokenTableActionsComponent } from "./token-table-actions.component";
import { DocumentationService } from "@services/documentation/documentation.service";
import { DialogService } from "@services/dialog/dialog.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { FilterValue } from "@core/models/filter_value/filter_value";

describe("TokenTableActionsComponent", () => {
  let component: TokenTableActionsComponent;
  let fixture: ComponentFixture<TokenTableActionsComponent>;

  let tokenService: jest.Mocked<MockTokenService>;
  let dialogService: MockDialogService;
  let notificationService: jest.Mocked<NotificationServiceInterface>;
  let router: MockRouter;
  let tableUtilsService: MockTableUtilsService;

  beforeEach(async () => {
    const dialogMock = {
      open: jest.fn().mockReturnValue({
        afterClosed: () => of({ confirmed: true })
      } as unknown as MatDialogRef<SimpleConfirmationDialogComponent>)
    };

    await TestBed.configureTestingModule({
      imports: [TokenTableActionsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useClass: MockRouter },
        { provide: ActivatedRoute, useValue: { params: of({ id: "123" }) } },
        { provide: TokenService, useClass: MockTokenService },
        { provide: MatDialog, useValue: dialogMock },
        { provide: VersioningService, useClass: MockVersioningService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService },
        { provide: AuditService, useClass: MockAuditService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: DocumentationService, useClass: MockDocumentationService },
        { provide: TableUtilsService, useClass: MockTableUtilsService }
      ]
    }).compileComponents();
    fixture = TestBed.createComponent(TokenTableActionsComponent);
    component = fixture.componentInstance;

    tokenService = TestBed.inject(TokenService) as unknown as jest.Mocked<MockTokenService>;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    // Default: dialog confirms with truthy result
    (dialogService.openDialog as jest.Mock).mockImplementation(() => ({
      afterClosed: () => of(true)
    }));
    notificationService = TestBed.inject(NotificationService) as unknown as jest.Mocked<NotificationServiceInterface>;
    router = TestBed.inject(Router) as unknown as MockRouter;
    tableUtilsService = TestBed.inject(TableUtilsService) as unknown as MockTableUtilsService;

    fixture.detectChanges();
  });

  /** Helper: make dialogService.openDialog return a ref that auto-closes with `result`. */
  function mockDialogResult(result: unknown): void {
    (dialogService.openDialog as jest.Mock).mockImplementation(() => ({
      afterClosed: () => of(result)
    }));
  }

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

      expect(dialogService.openDialog).toHaveBeenCalled();
      expect(tokenService.revokeToken).toHaveBeenCalledWith("MOCK_SERIAL");
      expect(tokenService.getTokenDetails).toHaveBeenCalledWith("MOCK_SERIAL");
      expect(tokenService.tokenDetailResource.reload).toHaveBeenCalled();
    });
  });

  describe("deleteToken()", () => {
    it("opens confirm dialog, deletes and navigates", () => {
      component.tokenSerial.set("MOCK_SERIAL");
      component.deleteToken();

      expect(dialogService.openDialog).toHaveBeenCalled();
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
      const bulkUnassignResponse = new MockPiResponse<BulkResult, unknown>({
        detail: {},
        result: {
          status: true,
          value: { count_success: 1, failed: [], unauthorized: [] }
        }
      });

      const bulkUnassignSpy = jest.spyOn(tokenService, "bulkUnassignTokens").mockReturnValue(of(bulkUnassignResponse));

      const reloadSpy = jest.spyOn(tokenService.tokenResource, "reload");

      component.tokenSelection.set(mockTokens);
      component.unassignSelectedTokens();

      expect(dialogService.openDialog).toHaveBeenCalled();
      expect(bulkUnassignSpy).toHaveBeenCalledWith(mockTokens);
      expect(notificationService.success).toHaveBeenCalledWith("Successfully unassigned 1 token.");
      expect(reloadSpy).toHaveBeenCalled();
    });
  });

  describe("assignSelectedTokens()", () => {
    it("should do nothing if dialog is cancelled", () => {
      mockDialogResult(null);

      component.assignSelectedTokens();

      expect(tokenService.assignUser).not.toHaveBeenCalled();
      expect(tokenService.unassignUser).not.toHaveBeenCalled();
    });

    it("should assign tokens without an existing user", () => {
      const tokens = [{ serial: "T1", username: "" }] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);
      mockDialogResult({ username: "new_user", realm: "new_realm" });

      component.assignSelectedTokens();

      expect(tokenService.unassignUser).not.toHaveBeenCalled();
      expect(tokenService.assignUser).toHaveBeenCalledWith({
        tokenSerial: "T1",
        username: "new_user",
        realm: "new_realm"
      });
      expect(tokenService.tokenResource.reload).toHaveBeenCalled();
    });

    it("should unassign and then re-assign tokens that already have a user", () => {
      const tokens = [{ serial: "T1", username: "old_user" }] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);
      mockDialogResult({ username: "new_user", realm: "new_realm" });

      component.assignSelectedTokens();

      expect(tokenService.unassignUser).toHaveBeenCalledWith("T1");
      expect(tokenService.assignUser).toHaveBeenCalledWith({
        tokenSerial: "T1",
        username: "new_user",
        realm: "new_realm"
      });
      expect(tokenService.tokenResource.reload).toHaveBeenCalled();
    });
  });

  describe("toggleActiveSelectedTokens()", () => {
    it("should do nothing when no tokens are selected", () => {
      tokenService.tokenSelection.set([]);
      component.toggleActiveSelectedTokens();
      // openDialog was already called in beforeEach default setup, reset to check
      (dialogService.openDialog as jest.Mock).mockClear();
      tokenService.tokenSelection.set([]);
      component.toggleActiveSelectedTokens();
      expect(dialogService.openDialog).not.toHaveBeenCalled();
    });

    it("should toggle all tokens when dialog returns 'toggle'", () => {
      const tokens = [
        { serial: "T1", active: true },
        { serial: "T2", active: false }
      ] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);
      mockDialogResult("toggle");

      component.toggleActiveSelectedTokens();

      expect(tokenService.toggleActive).toHaveBeenCalledWith("T1", true);
      expect(tokenService.toggleActive).toHaveBeenCalledWith("T2", false);
      expect(notificationService.success).toHaveBeenCalledWith("Successfully toggled 2 token(s).");
    });

    it("should only activate inactive tokens when dialog returns 'activate'", () => {
      const tokens = [
        { serial: "T1", active: true },
        { serial: "T2", active: false }
      ] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);
      mockDialogResult("activate");

      component.toggleActiveSelectedTokens();

      expect(tokenService.toggleActive).toHaveBeenCalledWith("T2", false);
      expect(notificationService.success).toHaveBeenCalledWith("Successfully activated 1 token(s).");
    });

    it("should only deactivate active tokens when dialog returns 'deactivate'", () => {
      const tokens = [
        { serial: "T1", active: true },
        { serial: "T2", active: false }
      ] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);
      mockDialogResult("deactivate");

      component.toggleActiveSelectedTokens();

      expect(tokenService.toggleActive).toHaveBeenCalledWith("T1", true);
      expect(notificationService.success).toHaveBeenCalledWith("Successfully deactivated 1 token(s).");
    });

    it("should show 'No tokens to process' when activate is chosen but all are already active", () => {
      const tokens = [{ serial: "T1", active: true }] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);
      mockDialogResult("activate");

      component.toggleActiveSelectedTokens();

      expect(notificationService.success).toHaveBeenCalledWith("No tokens to process.");
    });

    it("should do nothing when dialog is cancelled", () => {
      const tokens = [{ serial: "T1", active: true }] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);
      mockDialogResult(undefined);

      component.toggleActiveSelectedTokens();

      expect(tokenService.toggleActive).not.toHaveBeenCalled();
    });

    it("should handle error during toggle", () => {
      const tokens = [{ serial: "T1", active: true }] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);
      mockDialogResult("toggle");
      (tokenService.toggleActive as jest.Mock).mockReturnValue(
        throwError(() => ({ error: { result: { error: { message: "Toggle failed" } } } }))
      );

      component.toggleActiveSelectedTokens();

      expect(notificationService.error).toHaveBeenCalledWith("Toggle failed");
    });

    it("should show generic error when error has no message", () => {
      const tokens = [{ serial: "T1", active: true }] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);
      mockDialogResult("toggle");
      (tokenService.toggleActive as jest.Mock).mockReturnValue(throwError(() => ({})));

      component.toggleActiveSelectedTokens();

      expect(notificationService.error).toHaveBeenCalledWith("An error occurred while toggling tokens.");
    });
  });

  describe("resetFailcounterSelectedTokens()", () => {
    it("should do nothing when no tokens are selected", () => {
      (dialogService.openDialog as jest.Mock).mockClear();
      tokenService.tokenSelection.set([]);
      component.resetFailcounterSelectedTokens();
      expect(dialogService.openDialog).not.toHaveBeenCalled();
    });

    it("should reset failcounters on confirmation", () => {
      const tokens = [{ serial: "T1" }, { serial: "T2" }] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);
      mockDialogResult(true);

      component.resetFailcounterSelectedTokens();

      expect(tokenService.resetFailCount).toHaveBeenCalledWith("T1");
      expect(tokenService.resetFailCount).toHaveBeenCalledWith("T2");
      expect(notificationService.success).toHaveBeenCalledWith("Successfully reset failcounter for 2 token(s).");
      expect(tokenService.tokenResource.reload).toHaveBeenCalled();
      expect(tokenService.tokenDetailResource.reload).toHaveBeenCalled();
    });

    it("should do nothing when dialog is cancelled", () => {
      const tokens = [{ serial: "T1" }] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);
      mockDialogResult(undefined);

      component.resetFailcounterSelectedTokens();

      expect(tokenService.resetFailCount).not.toHaveBeenCalled();
    });

    it("should handle error with server message", () => {
      const tokens = [{ serial: "T1" }] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);
      mockDialogResult(true);
      (tokenService.resetFailCount as jest.Mock).mockReturnValue(
        throwError(() => ({ error: { result: { error: { message: "Reset failed" } } } }))
      );

      component.resetFailcounterSelectedTokens();

      expect(notificationService.error).toHaveBeenCalledWith("Reset failed");
    });

    it("should handle error without server message", () => {
      const tokens = [{ serial: "T1" }] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);
      mockDialogResult(true);
      (tokenService.resetFailCount as jest.Mock).mockReturnValue(throwError(() => ({})));

      component.resetFailcounterSelectedTokens();

      expect(notificationService.error).toHaveBeenCalledWith("An error occurred while resetting failcounters.");
    });
  });

  describe("isFilterSelected()", () => {
    it("should return true for infokey & infovalue when both keys are present", () => {
      const filter = new FilterValue({ value: "infokey: key1 infovalue: val1" });
      tokenService.tokenFilter.set(filter);
      expect(component.isFilterSelected("infokey & infovalue")).toBe(true);
    });

    it("should return false for infokey & infovalue when only one key is present", () => {
      const filter = new FilterValue({ value: "infokey: key1" });
      tokenService.tokenFilter.set(filter);
      expect(component.isFilterSelected("infokey & infovalue")).toBe(false);
    });

    it("should return true for a regular filter when key is present", () => {
      const filter = new FilterValue({ value: "type: hotp" });
      tokenService.tokenFilter.set(filter);
      expect(component.isFilterSelected("type")).toBe(true);
    });

    it("should return false for a regular filter when key is not present", () => {
      const filter = new FilterValue();
      tokenService.tokenFilter.set(filter);
      expect(component.isFilterSelected("type")).toBe(false);
    });
  });

  describe("getFilterIconName()", () => {
    it("should return 'filter_alt' when active filter has no value", () => {
      const filter = new FilterValue();
      tokenService.tokenFilter.set(filter);
      expect(component.getFilterIconName("active")).toBe("filter_alt");
    });

    it("should return 'screen_rotation_alt' when active is 'true'", () => {
      const filter = new FilterValue({ value: "active: true" });
      tokenService.tokenFilter.set(filter);
      expect(component.getFilterIconName("active")).toBe("screen_rotation_alt");
    });

    it("should return 'filter_alt_off' when active is 'false'", () => {
      const filter = new FilterValue({ value: "active: false" });
      tokenService.tokenFilter.set(filter);
      expect(component.getFilterIconName("active")).toBe("filter_alt_off");
    });

    it("should return 'filter_alt' when active has an unknown value", () => {
      const filter = new FilterValue({ value: "active: maybe" });
      tokenService.tokenFilter.set(filter);
      expect(component.getFilterIconName("active")).toBe("filter_alt");
    });

    it("should return 'filter_alt_off' when a non-boolean keyword is selected", () => {
      const filter = new FilterValue({ value: "type: hotp" });
      tokenService.tokenFilter.set(filter);
      expect(component.getFilterIconName("type")).toBe("filter_alt_off");
    });

    it("should return 'filter_alt' when a non-boolean keyword is not selected", () => {
      const filter = new FilterValue();
      tokenService.tokenFilter.set(filter);
      expect(component.getFilterIconName("type")).toBe("filter_alt");
    });

    it("should work for 'assigned' keyword with 'true' value", () => {
      const filter = new FilterValue({ value: "assigned: true" });
      tokenService.tokenFilter.set(filter);
      expect(component.getFilterIconName("assigned")).toBe("screen_rotation_alt");
    });
  });

  describe("onAdvancedFilterClick()", () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });
    afterEach(() => {
      jest.useRealTimers();
    });

    it("should call toggleBooleanInFilter for 'assigned' keyword", () => {
      const filter = new FilterValue();
      tokenService.tokenFilter.set(filter);
      component.onAdvancedFilterClick("assigned");
      expect(tableUtilsService.toggleBooleanInFilter).toHaveBeenCalledWith({
        keyword: "assigned",
        currentValue: filter
      });
    });

    it("should add both infokey and infovalue when neither is present", () => {
      const filter = new FilterValue();
      tokenService.tokenFilter.set(filter);
      component.onAdvancedFilterClick("infokey & infovalue");
      expect(tableUtilsService.toggleKeywordInFilter).toHaveBeenCalledWith({
        keyword: "infokey",
        currentValue: filter
      });
      expect(tableUtilsService.toggleKeywordInFilter).toHaveBeenCalledTimes(2);
    });

    it("should remove both infokey and infovalue when both are present", () => {
      const filter = new FilterValue({ value: "infokey: k infovalue: v" });
      tokenService.tokenFilter.set(filter);
      component.onAdvancedFilterClick("infokey & infovalue");
      expect(tableUtilsService.toggleKeywordInFilter).toHaveBeenCalledTimes(2);
    });

    it("should add infovalue when only infokey is present", () => {
      const filter = new FilterValue({ value: "infokey: k" });
      tokenService.tokenFilter.set(filter);
      component.onAdvancedFilterClick("infokey & infovalue");
      expect(tableUtilsService.toggleKeywordInFilter).toHaveBeenCalledWith({
        keyword: "infovalue",
        currentValue: filter
      });
      expect(tableUtilsService.toggleKeywordInFilter).toHaveBeenCalledTimes(1);
    });

    it("should add infokey when only infovalue is present", () => {
      const filter = new FilterValue({ value: "infovalue: v" });
      tokenService.tokenFilter.set(filter);
      component.onAdvancedFilterClick("infokey & infovalue");
      expect(tableUtilsService.toggleKeywordInFilter).toHaveBeenCalledWith({
        keyword: "infokey",
        currentValue: filter
      });
      expect(tableUtilsService.toggleKeywordInFilter).toHaveBeenCalledTimes(1);
    });

    it("should call toggleKeywordInFilter for generic keywords", () => {
      const filter = new FilterValue();
      tokenService.tokenFilter.set(filter);
      component.onAdvancedFilterClick("type");
      expect(tableUtilsService.toggleKeywordInFilter).toHaveBeenCalledWith({
        keyword: "type",
        currentValue: filter
      });
    });

    it("should focus the filter input after toggle", () => {
      const filter = new FilterValue();
      tokenService.tokenFilter.set(filter);
      const mockInput = document.createElement("input");
      mockInput.id = "token-filter-input";
      document.body.appendChild(mockInput);
      const focusSpy = jest.spyOn(mockInput, "focus");

      component.onAdvancedFilterClick("type");
      jest.advanceTimersByTime(10);

      expect(focusSpy).toHaveBeenCalled();
      document.body.removeChild(mockInput);
    });
  });

  describe("unassignSelectedTokens() - additional branches", () => {
    it("should show failed and unauthorized messages", () => {
      const tokens = [{ serial: "T1" }, { serial: "T2" }, { serial: "T3" }] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);

      const bulkResponse = new MockPiResponse<BulkResult, unknown>({
        detail: {},
        result: {
          status: true,
          value: { count_success: 1, failed: ["T2"], unauthorized: ["T3"] }
        }
      });
      jest.spyOn(tokenService, "bulkUnassignTokens").mockReturnValue(of(bulkResponse));
      mockDialogResult(true);

      component.tokenSelection.set(tokens);
      component.unassignSelectedTokens();

      expect(notificationService.success).toHaveBeenCalledWith(
        expect.stringContaining("Successfully unassigned 1 token.")
      );
      expect(notificationService.success).toHaveBeenCalledWith(
        expect.stringContaining("The following tokens failed to unassign: T2")
      );
      expect(notificationService.success).toHaveBeenCalledWith(
        expect.stringContaining("You are not authorized to unassign the following tokens: T3")
      );
    });

    it("should show plural message for multiple successful unassigns", () => {
      const tokens = [{ serial: "T1" }, { serial: "T2" }] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);

      const bulkResponse = new MockPiResponse<BulkResult, unknown>({
        detail: {},
        result: {
          status: true,
          value: { count_success: 2, failed: [], unauthorized: [] }
        }
      });
      jest.spyOn(tokenService, "bulkUnassignTokens").mockReturnValue(of(bulkResponse));
      mockDialogResult(true);

      component.tokenSelection.set(tokens);
      component.unassignSelectedTokens();

      expect(notificationService.success).toHaveBeenCalledWith("Successfully unassigned 2 tokens.");
    });

    it("should handle error during bulk unassign", () => {
      const tokens = [{ serial: "T1" }] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);

      jest
        .spyOn(tokenService, "bulkUnassignTokens")
        .mockReturnValue(throwError(() => ({ error: { result: { error: { message: "Not allowed" } } } })));
      mockDialogResult(true);

      component.tokenSelection.set(tokens);
      component.unassignSelectedTokens();

      expect(notificationService.error).toHaveBeenCalledWith("Not allowed");
    });

    it("should handle error without server message during bulk unassign", () => {
      const tokens = [{ serial: "T1" }] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);

      jest.spyOn(tokenService, "bulkUnassignTokens").mockReturnValue(throwError(() => ({})));
      mockDialogResult(true);

      component.tokenSelection.set(tokens);
      component.unassignSelectedTokens();

      expect(notificationService.error).toHaveBeenCalledWith("An error occurred while unassigning tokens.");
    });

    it("should do nothing when unassign dialog is cancelled", () => {
      const tokens = [{ serial: "T1" }] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);
      mockDialogResult(undefined);

      component.tokenSelection.set(tokens);
      component.unassignSelectedTokens();

      expect(tokenService.bulkUnassignTokens).not.toHaveBeenCalled();
    });
  });

  describe("assignSelectedTokens() - error handling", () => {
    it("should show error notification with server message on assign failure", () => {
      const tokens = [{ serial: "T1", username: "" }] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);

      (tokenService.assignUser as jest.Mock).mockReturnValue(
        throwError(() => ({ error: { result: { error: { message: "Assign failed" } } } }))
      );
      mockDialogResult({ username: "user1", realm: "realm1" });

      component.assignSelectedTokens();

      expect(notificationService.error).toHaveBeenCalledWith("Assign failed");
    });

    it("should show generic error notification on assign failure without message", () => {
      const tokens = [{ serial: "T1", username: "" }] as TokenDetails[];
      tokenService.tokenSelection.set(tokens);

      (tokenService.assignUser as jest.Mock).mockReturnValue(throwError(() => ({})));
      mockDialogResult({ username: "user1", realm: "realm1" });

      component.assignSelectedTokens();

      expect(notificationService.error).toHaveBeenCalledWith("An error occurred while assigning tokens.");
    });
  });
});
