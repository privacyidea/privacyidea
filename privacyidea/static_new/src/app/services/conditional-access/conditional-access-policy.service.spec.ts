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
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { signal } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { MockContentService, MockDialogService, MockNotificationService, MockPiResponse } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { ConditionalAccessPolicyService, LockoutPolicy } from "./conditional-access-policy.service";

describe("ConditionalAccessPolicyService", () => {
  let service: ConditionalAccessPolicyService;
  let httpMock: HttpTestingController;
  let notificationServiceMock: MockNotificationService;
  let contentServiceMock: MockContentService;
  let authServiceMock: MockAuthService;
  let dialogServiceMock: MockDialogService;

  const samplePolicy: LockoutPolicy = {
    id: 1,
    name: "Brute Force",
    time_window_seconds: 600,
    enabled: true,
    dry_run: false,
    priority: 1,
    target: "user",
    counter_types_to_track: ["PIN_FAIL"],
    stages: [
      {
        id: 1,
        failure_threshold: 5,
        priority: 1,
        actions: [{ id: 1, action_type: "LOCK_USER", action_value: { lock_duration_seconds: 600 } }]
      }
    ]
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        ConditionalAccessPolicyService,
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    });
    service = TestBed.inject(ConditionalAccessPolicyService);
    httpMock = TestBed.inject(HttpTestingController);
    notificationServiceMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    contentServiceMock = TestBed.inject(ContentService) as unknown as MockContentService;
    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    authServiceMock.actionAllowed.mockReturnValue(true);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  describe("policies", () => {
    it("should default to empty array when resource has not fired", () => {
      expect(service.policies()).toEqual([]);
    });

    it("should not fetch when the read right is missing", () => {
      authServiceMock.actionAllowed.mockReturnValue(false);
      contentServiceMock.onConditionalAccess = signal(true);
      TestBed.tick();
      httpMock.expectNone(service.baseUrl);
    });

    it("should not fetch when not on the conditional-access route", () => {
      contentServiceMock.onConditionalAccess = signal(false);
      TestBed.tick();
      httpMock.expectNone(service.baseUrl);
    });

    it("should load policies from the resource", async () => {
      contentServiceMock.onConditionalAccess = signal(true);
      TestBed.tick();

      const req = httpMock.expectOne(service.baseUrl);
      expect(req.request.method).toBe("GET");
      req.flush(MockPiResponse.fromValue([samplePolicy]));
      httpMock.expectOne(service.eventTypesUrl).flush(MockPiResponse.fromValue([]));
      httpMock.expectOne(service.actionTypesUrl).flush(MockPiResponse.fromValue([]));
      httpMock.expectOne(service.targetsUrl).flush(MockPiResponse.fromValue({}));
      httpMock.expectOne(service.templatesUrl).flush(MockPiResponse.fromValue([]));
      await Promise.resolve();

      expect(service.policies()).toEqual([samplePolicy]);
    });

    it("should fall back to an empty array on error", async () => {
      contentServiceMock.onConditionalAccess = signal(true);
      TestBed.tick();

      const req = httpMock.expectOne(service.baseUrl);
      req.flush(MockPiResponse.fromError({ message: "denied" }), { status: 403, statusText: "Forbidden" });
      httpMock.expectOne(service.eventTypesUrl).flush(MockPiResponse.fromValue([]));
      httpMock.expectOne(service.actionTypesUrl).flush(MockPiResponse.fromValue([]));
      httpMock.expectOne(service.targetsUrl).flush(MockPiResponse.fromValue({}));
      httpMock.expectOne(service.templatesUrl).flush(MockPiResponse.fromValue([]));
      await Promise.resolve();

      expect(service.policies()).toEqual([]);
    });
  });

  describe("constant lists", () => {
    it("should load event types and action types from the backend", async () => {
      contentServiceMock.onConditionalAccess = signal(true);
      TestBed.tick();

      httpMock.expectOne(service.baseUrl).flush(MockPiResponse.fromValue([]));
      httpMock.expectOne(service.eventTypesUrl).flush(MockPiResponse.fromValue(["PIN_FAIL", "MFA_FAIL"]));
      httpMock.expectOne(service.actionTypesUrl).flush(MockPiResponse.fromValue(["LOCK_USER", "ALLOW"]));
      httpMock.expectOne(service.targetsUrl).flush(MockPiResponse.fromValue({}));
      httpMock.expectOne(service.templatesUrl).flush(MockPiResponse.fromValue([]));
      await Promise.resolve();

      expect(service.eventTypes()).toEqual(["PIN_FAIL", "MFA_FAIL"]);
      expect(service.actionTypes()).toEqual(["LOCK_USER", "ALLOW"]);
    });

    it("should not fetch the lists without the read right", () => {
      authServiceMock.actionAllowed.mockReturnValue(false);
      contentServiceMock.onConditionalAccess = signal(true);
      TestBed.tick();
      httpMock.expectNone(service.eventTypesUrl);
      httpMock.expectNone(service.actionTypesUrl);
    });
  });

  describe("targets and templates", () => {
    const targetConstraints = {
      user: { actions: ["LOCK_USER", "ALLOW", "DENY"], count_modes: ["PER_ATTEMPT", "PER_REQUEST"] },
      source_ip: {
        actions: ["BLOCK_IP", "ALLOW", "DENY"],
        count_modes: ["DISTINCT_USERS", "PER_ATTEMPT", "PER_REQUEST"]
      }
    };
    const expectedActionsByTarget = {
      user: ["LOCK_USER", "ALLOW", "DENY"],
      source_ip: ["BLOCK_IP", "ALLOW", "DENY"]
    };
    const expectedCountModesByTarget = {
      user: ["PER_ATTEMPT", "PER_REQUEST"],
      source_ip: ["DISTINCT_USERS", "PER_ATTEMPT", "PER_REQUEST"]
    };
    const sampleTemplate = {
      key: "password_bruteforce",
      description: "Lock a user after repeated wrong passwords.",
      policy: {
        name: "Password Brute-Force",
        time_window_seconds: 900,
        enabled: true,
        dry_run: false,
        priority: 1,
        target: "user" as const,
        count_mode: "PER_REQUEST" as const,
        counter_types_to_track: ["PASSWORD_FAIL" as const],
        stages: [
          { failure_threshold: 10, priority: 1, actions: [{ action_type: "LOCK_USER" as const, action_value: null }] }
        ]
      }
    };

    async function load(): Promise<void> {
      contentServiceMock.onConditionalAccess = signal(true);
      TestBed.tick();
      httpMock.expectOne(service.baseUrl).flush(MockPiResponse.fromValue([]));
      httpMock.expectOne(service.eventTypesUrl).flush(MockPiResponse.fromValue([]));
      httpMock.expectOne(service.actionTypesUrl).flush(MockPiResponse.fromValue(["LOCK_USER", "ALLOW", "DENY"]));
      httpMock.expectOne(service.targetsUrl).flush(MockPiResponse.fromValue(targetConstraints));
      httpMock.expectOne(service.templatesUrl).flush(MockPiResponse.fromValue([sampleTemplate]));
      await Promise.resolve();
    }

    it("should default to empty derived values before the resources fire", () => {
      expect(service.actionsByTarget()).toEqual({});
      expect(service.countModesByTarget()).toEqual({});
      expect(service.targets()).toEqual([]);
      expect(service.templates()).toEqual([]);
    });

    it("should derive actionsByTarget, countModesByTarget and targets from the /targets response", async () => {
      await load();
      expect(service.actionsByTarget()).toEqual(expectedActionsByTarget);
      expect(service.countModesByTarget()).toEqual(expectedCountModesByTarget);
      expect(service.targets()).toEqual(["user", "source_ip"]);
    });

    it("should load templates from the /template response", async () => {
      await load();
      expect(service.templates()).toEqual([sampleTemplate]);
    });

    it("should return the allowed actions for a known target", async () => {
      await load();
      expect(service.actionsForTarget("user")).toEqual(["LOCK_USER", "ALLOW", "DENY"]);
      expect(service.actionsForTarget("source_ip")).toEqual(["BLOCK_IP", "ALLOW", "DENY"]);
    });

    it("should return the supported count modes for a known target", async () => {
      await load();
      expect(service.countModesForTarget("user")).toEqual(["PER_ATTEMPT", "PER_REQUEST"]);
      expect(service.countModesForTarget("source_ip")).toEqual(["DISTINCT_USERS", "PER_ATTEMPT", "PER_REQUEST"]);
    });

    it("should return no count modes for an unmapped target", async () => {
      await load();
      expect(service.countModesForTarget("unknown" as never)).toEqual([]);
    });

    it("should fall back to the full action-type list for an unmapped target", async () => {
      contentServiceMock.onConditionalAccess = signal(true);
      TestBed.tick();
      httpMock.expectOne(service.baseUrl).flush(MockPiResponse.fromValue([]));
      httpMock.expectOne(service.eventTypesUrl).flush(MockPiResponse.fromValue([]));
      httpMock.expectOne(service.actionTypesUrl).flush(MockPiResponse.fromValue(["LOCK_USER", "ALLOW", "DENY"]));
      httpMock.expectOne(service.targetsUrl).flush(MockPiResponse.fromValue({}));
      httpMock.expectOne(service.templatesUrl).flush(MockPiResponse.fromValue([]));
      await Promise.resolve();

      expect(service.actionsForTarget("user")).toEqual(["LOCK_USER", "ALLOW", "DENY"]);
    });

    it("should not fetch targets or templates without the read right", () => {
      authServiceMock.actionAllowed.mockReturnValue(false);
      contentServiceMock.onConditionalAccess = signal(true);
      TestBed.tick();
      httpMock.expectNone(service.targetsUrl);
      httpMock.expectNone(service.templatesUrl);
    });

    it("should not fetch targets or templates when not on the conditional-access route", () => {
      contentServiceMock.onConditionalAccess = signal(false);
      TestBed.tick();
      httpMock.expectNone(service.targetsUrl);
      httpMock.expectNone(service.templatesUrl);
    });
  });

  describe("savePolicy", () => {
    it("should POST to the base URL when creating (no id)", async () => {
      const promise = service.savePolicy({
        name: "New",
        time_window_seconds: 600,
        enabled: true,
        dry_run: false,
        priority: 1,
        counter_types_to_track: ["PIN_FAIL"],
        stages: []
      });

      const req = httpMock.expectOne(service.baseUrl);
      expect(req.request.method).toBe("POST");
      req.flush(MockPiResponse.fromValue(42));

      const id = await promise;
      expect(id).toBe(42);
      expect(notificationServiceMock.success).toHaveBeenCalled();
    });

    it("should PATCH to the id URL when updating (id present)", async () => {
      const promise = service.savePolicy({ ...samplePolicy });

      const req = httpMock.expectOne(`${service.baseUrl}/1`);
      expect(req.request.method).toBe("PATCH");
      req.flush(MockPiResponse.fromValue(1));

      await promise;
      expect(notificationServiceMock.success).toHaveBeenCalled();
    });

    it("should return undefined and notify on error", async () => {
      const promise = service.savePolicy({ ...samplePolicy });

      const req = httpMock.expectOne(`${service.baseUrl}/1`);
      req.flush(MockPiResponse.fromError({ message: "bad name" }), { status: 400, statusText: "Bad Request" });

      const id = await promise;
      expect(id).toBeUndefined();
      expect(notificationServiceMock.error).toHaveBeenCalledWith("Failed to save conditional-access policy. bad name");
    });
  });

  describe("deletePolicy", () => {
    it("should DELETE by id", async () => {
      const promise = service.deletePolicy(1);

      const req = httpMock.expectOne(`${service.baseUrl}/1`);
      expect(req.request.method).toBe("DELETE");
      req.flush(MockPiResponse.fromValue(1));

      await promise;
      expect(notificationServiceMock.success).toHaveBeenCalled();
    });

    it("should notify on error", async () => {
      const promise = service.deletePolicy(1);

      const req = httpMock.expectOne(`${service.baseUrl}/1`);
      req.flush(null, { status: 500, statusText: "Internal Server Error" });

      await promise;
      expect(notificationServiceMock.error).toHaveBeenCalled();
    });
  });

  describe("deleteWithConfirmDialog", () => {
    it("should delete when confirmed", async () => {
      dialogServiceMock.confirm.mockResolvedValue(true);
      const promise = service.deleteWithConfirmDialog({ id: 1, name: "Brute Force" });
      await Promise.resolve(); // let confirm() resolve before the delete request is issued

      const req = httpMock.expectOne(`${service.baseUrl}/1`);
      req.flush(MockPiResponse.fromValue(1));

      await promise;
      expect(dialogServiceMock.confirm).toHaveBeenCalled();
    });

    it("should not delete when not confirmed", async () => {
      dialogServiceMock.confirm.mockResolvedValue(false);
      await service.deleteWithConfirmDialog({ id: 1, name: "Brute Force" });

      httpMock.expectNone(`${service.baseUrl}/1`);
    });
  });

  describe("deleteSelectedWithConfirmDialog", () => {
    it("should return false without asking when the list is empty", async () => {
      const result = await service.deleteSelectedWithConfirmDialog([]);
      expect(result).toBe(false);
      expect(dialogServiceMock.confirm).not.toHaveBeenCalled();
    });

    it("should delete every selected policy when confirmed", async () => {
      dialogServiceMock.confirm.mockResolvedValue(true);
      const promise = service.deleteSelectedWithConfirmDialog([
        { id: 1, name: "Brute Force" },
        { id: 2, name: "Second" }
      ]);
      await Promise.resolve(); // let confirm() resolve before the delete requests are issued

      httpMock.expectOne(`${service.baseUrl}/1`).flush(MockPiResponse.fromValue(1));
      httpMock.expectOne(`${service.baseUrl}/2`).flush(MockPiResponse.fromValue(2));

      expect(await promise).toBe(true);
    });

    it("should not issue requests when not confirmed", async () => {
      dialogServiceMock.confirm.mockResolvedValue(false);
      const result = await service.deleteSelectedWithConfirmDialog([{ id: 1, name: "Brute Force" }]);

      expect(result).toBe(false);
      httpMock.expectNone(`${service.baseUrl}/1`);
    });
  });

  describe("enablePolicy / disablePolicy", () => {
    it("should PATCH to enable", async () => {
      const promise = service.enablePolicy(1);
      const req = httpMock.expectOne(`${service.baseUrl}/1`);
      expect(req.request.method).toBe("PATCH");
      expect(req.request.body).toEqual({ enabled: true });
      req.flush({});
      await promise;
    });

    it("should PATCH to disable", async () => {
      const promise = service.disablePolicy(1);
      const req = httpMock.expectOne(`${service.baseUrl}/1`);
      expect(req.request.method).toBe("PATCH");
      expect(req.request.body).toEqual({ enabled: false });
      req.flush({});
      await promise;
    });

    it("should notify on enable error", async () => {
      const promise = service.enablePolicy(1);
      const req = httpMock.expectOne(`${service.baseUrl}/1`);
      req.flush(null, { status: 500, statusText: "Internal Server Error" });
      await promise;
      expect(notificationServiceMock.error).toHaveBeenCalled();
    });

    it("should notify on disable error", async () => {
      const promise = service.disablePolicy(1);
      const req = httpMock.expectOne(`${service.baseUrl}/1`);
      req.flush(null, { status: 500, statusText: "Internal Server Error" });
      await promise;
      expect(notificationServiceMock.error).toHaveBeenCalled();
    });
  });
});
