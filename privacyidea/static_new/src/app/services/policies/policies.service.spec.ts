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

import { TestBed } from "@angular/core/testing";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { provideHttpClient } from "@angular/common/http";
import { PolicyActionDetail, PolicyDetail, PolicyService } from "./policies.service";
import { AuthService } from "../auth/auth.service";
import { ContentService } from "../content/content.service";
import { NotificationService } from "../notification/notification.service";
import { MockContentService, MockPiResponse } from "src/testing/mock-services";
import { MockAuthService } from "src/testing/mock-services/mock-auth-service";
import { MockNotificationService } from "src/testing/mock-services/mock-notification-service";
import { signal } from "@angular/core";

describe("PolicyService", () => {
  let service: PolicyService;
  let httpTestingController: HttpTestingController;
  let notificationService: MockNotificationService;
  let authService: MockAuthService;
  let contentService: MockContentService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        PolicyService,
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    });
    service = TestBed.inject(PolicyService);
    httpTestingController = TestBed.inject(HttpTestingController);
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    contentService = TestBed.inject(ContentService) as unknown as MockContentService;
  });
  afterEach(() => {
    httpTestingController.verify();
  });
  it("should be created", () => {
    expect(service).toBeTruthy();
  });
  describe("Logic Methods", () => {
    it("should return an empty policy structure", () => {
      const empty = service.getEmptyPolicy();
      expect(empty.name).toBe("");
      expect(empty.active).toBeTruthy();
      expect(Array.isArray(empty.realm)).toBeTruthy();
    });
    it("should validate if a policy can be saved", () => {
      const policy = service.getEmptyPolicy();
      expect(service.canSavePolicy(policy)).toBeFalsy();
      policy.name = "TestPolicy";
      policy.scope = "user";
      policy.action = { "test-action": true };
      expect(service.canSavePolicy(policy)).toBeTruthy();
    });
    it("should correctly identify edited policies", () => {
      const original = service.getEmptyPolicy();
      const edited = { ...original, description: "New Description" };
      expect(service.isPolicyEdited(edited, original)).toBeTruthy();
      expect(service.isPolicyEdited(original, original)).toBeFalsy();
    });
  });
  describe("Condition Checks", () => {
    it("should detect user conditions", () => {
      const policy = service.getEmptyPolicy();
      policy.realm = ["realm1"];
      expect(service.policyHasUserConditions(policy)).toBeTruthy();
    });
    it("should detect environment conditions", () => {
      const policy = service.getEmptyPolicy();
      policy.client = ["127.0.0.1"];
      expect(service.policyHasEnvironmentConditions(policy)).toBeTruthy();
    });
    it("should detect additional conditions", () => {
      const policy = service.getEmptyPolicy();
      policy.conditions = [["userinfo", "key", "equals", "value", false, "raise_error"]];
      expect(service.policyHasAdditionalConditions(policy)).toBeTruthy();
    });
  });
  describe("HTTP Actions & Signals", () => {
    it("should send a POST request when saving policy edits (optimistic update)", () => {
      const policyName = "test-policy";
      const policy = service.getEmptyPolicy();
      policy.name = policyName;

      service.allPolicies.set([policy]);

      const changes = { description: "updated description" };
      service.savePolicyEdits("test/policy", { ...policy, ...changes, name: "test/policy" });

      const req = httpTestingController.expectOne(`${service.policyBaseUrl}${encodeURIComponent("test/policy")}`);

      expect(req.request.method).toBe("POST");
      expect(req.request.body).toMatchObject(changes);

      req.flush(MockPiResponse.fromValue({}));
    });
    it("should toggle policy active state optimistically", () => {
      const policy: PolicyDetail = { ...service.getEmptyPolicy(), name: "test/1", active: true };
      service.allPolicies.set([policy]);
      service.togglePolicyActive(policy);
      expect(service.allPolicies()[0].active).toBeFalsy();
      const req = httpTestingController.expectOne(`${service.policyBaseUrl}disable/${encodeURIComponent("test/1")}`);
      req.flush(MockPiResponse.fromValue({}));
    });
    it("should delete a policy and update the signal", async () => {
      const policy = { ...service.getEmptyPolicy(), name: "to/delete" };
      service.allPolicies.set([policy]);
      const deletePromise = service.deletePolicy("to/delete");
      const req = httpTestingController.expectOne(`${service.policyBaseUrl}${encodeURIComponent("to/delete")}`);
      expect(req.request.method).toBe("DELETE");
      req.flush(MockPiResponse.fromValue(1));
      const response = await deletePromise;
      expect(response.result?.value).toBe(1);
    });
  });
  describe("Validation Logic", () => {
    it("should validate action values correctly", () => {
      const boolAction: PolicyActionDetail = { type: "bool", desc: "test" };
      const intAction: PolicyActionDetail = { type: "int", desc: "test" };
      const strAction: PolicyActionDetail = { type: "str", desc: "test" };
      expect(service.actionValueIsValid(boolAction, "true")).toBeTruthy();
      expect(service.actionValueIsValid(boolAction, "invalid")).toBeFalsy();
      expect(service.actionValueIsValid(intAction, "123")).toBeTruthy();
      expect(service.actionValueIsValid(intAction, "12.5")).toBeFalsy();
      expect(service.actionValueIsValid(strAction, "Hello")).toBeTruthy();
      expect(service.actionValueIsValid(strAction, "  ")).toBeFalsy();
    });
  });
  describe("saveNewPolicy", () => {
    let newPolicy: PolicyDetail;

    beforeEach(() => {
      newPolicy = {
        ...service.getEmptyPolicy(),
        name: "new-test-policy",
        scope: "user",
        action: { "test-action": true }
      };
      // Reset notification service mock
      notificationService.openSnackBar.mockClear();
    });

    it("should return true and show success notification when policy is created successfully", async () => {
      service.allPolicies.set([]);
      const reloadSpy = jest.spyOn(service.allPoliciesResource, "reload");

      const savePromise = service.saveNewPolicy(newPolicy);

      const req = httpTestingController.expectOne(`${service.policyBaseUrl}${encodeURIComponent(newPolicy.name)}`);
      expect(req.request.method).toBe("POST");
      expect(req.request.body).toMatchObject(newPolicy);
      req.flush(MockPiResponse.fromValue({ status: true }));

      const result = await savePromise;
      expect(result).toBe(true);
      expect(notificationService.openSnackBar).toHaveBeenCalledWith(
        expect.stringContaining("Policy created successfully")
      );
      expect(reloadSpy).toHaveBeenCalled();
    });

    it("should return false and show error notification when response status is false", async () => {
      service.allPolicies.set([]);
      const reloadSpy = jest.spyOn(service.allPoliciesResource, "reload");
      const errorMessage = "Policy name already exists";

      const savePromise = service.saveNewPolicy(newPolicy);

      const req = httpTestingController.expectOne(`${service.policyBaseUrl}${encodeURIComponent(newPolicy.name)}`);
      req.flush(MockPiResponse.fromError({ message: errorMessage }));

      const result = await savePromise;
      expect(result).toBe(false);
      expect(notificationService.openSnackBar).toHaveBeenCalledWith(
        expect.stringContaining(`Creating policy failed: ${errorMessage}`)
      );
      expect(notificationService.openSnackBar).toHaveBeenCalledWith(expect.stringContaining(errorMessage));
      expect(reloadSpy).toHaveBeenCalled();
    });

    it("should handle HTTP error responses", async () => {
      service.allPolicies.set([]);
      const reloadSpy = jest.spyOn(service.allPoliciesResource, "reload");
      const errorMessage = "Scope required";

      const savePromise = service.saveNewPolicy(newPolicy);

      const req = httpTestingController.expectOne(`${service.policyBaseUrl}${encodeURIComponent(newPolicy.name)}`);
      const errorBody = {
        result: {
          error: {
            message: errorMessage
          }
        }
      };
      req.flush(errorBody, {
        status: 400,
        statusText: "Error"
      });

      const result = await savePromise;

      expect(result).toBe(false);
      expect(notificationService.openSnackBar).toHaveBeenCalledWith(
        expect.stringContaining(`Creating policy failed: ${errorMessage}`)
      );
      expect(reloadSpy).toHaveBeenCalled();
    });

    it("should handle errors without expected error structure", async () => {
      service.allPolicies.set([]);

      const savePromise = service.saveNewPolicy(newPolicy);

      const req = httpTestingController.expectOne(`${service.policyBaseUrl}${encodeURIComponent(newPolicy.name)}`);
      req.flush(null, {
        status: 0,
        statusText: "Unknown Error"
      });

      const result = await savePromise;

      expect(result).toBe(false);
      expect(notificationService.openSnackBar).toHaveBeenCalledWith(
        expect.stringContaining("Creating policy failed")
      );
    });
  });

  describe("savePolicyEdits", () => {
    let originalPolicy: PolicyDetail;
    let updatedPolicy: PolicyDetail;

    beforeEach(() => {
      originalPolicy = {
        ...service.getEmptyPolicy(),
        name: "existing-policy",
        scope: "user",
        action: { "test-action": true }
      };
      updatedPolicy = {
        ...originalPolicy,
        action: { "updated-action": true }
      };
      service.allPolicies.set([originalPolicy]);
      notificationService.openSnackBar.mockClear();
    });

    describe("Update policy without name change", () => {
      it("should successfully update policy and show success notification", async () => {
        const reloadSpy = jest.spyOn(service.allPoliciesResource, "reload");
        const savePromise = service.savePolicyEdits(originalPolicy.name, updatedPolicy);

        // Verify optimistic update
        expect(service.allPolicies()[0].action).toEqual({ "updated-action": true });

        // Handle POST request for update
        const postReq = httpTestingController.expectOne(`${service.policyBaseUrl}${originalPolicy.name}`);
        expect(postReq.request.method).toBe("POST");
        expect(postReq.request.body).toMatchObject(updatedPolicy);
        postReq.flush(MockPiResponse.fromValue({ status: true }));

        const result = await savePromise;
        expect(result).toBe(true);
        expect(reloadSpy).toHaveBeenCalled();
        expect(notificationService.openSnackBar).toHaveBeenCalledWith(
          expect.stringContaining("Policy updated successfully")
        );
      });

      it("should rollback optimistic update and show error notification on POST failure", async () => {
        const errorMessage = "Invalid action configuration";
        const savePromise = service.savePolicyEdits(originalPolicy.name, updatedPolicy);

        // Verify optimistic update
        expect(service.allPolicies()[0].action).toEqual({ "updated-action": true });

        // Simulate POST failure
        const postReq = httpTestingController.expectOne(`${service.policyBaseUrl}${originalPolicy.name}`);
        postReq.flush({
          result: {
            error: {
              message: errorMessage
            }
          }
        }, { status: 400, statusText: "Bad Request" });

        const result = await savePromise;

        expect(result).toBe(false);
        // Verify rollback - should still have original policy
        expect(service.allPolicies()[0].action).toEqual({ "test-action": true });
        expect(notificationService.openSnackBar).toHaveBeenCalledWith(
          expect.stringContaining(`Saving policy failed: ${errorMessage}`)
        );
      });
    });

    describe("Rename policy (update with name change)", () => {
      beforeEach(() => {
        updatedPolicy = {
          ...originalPolicy,
          name: "renamed-policy",
          action: { "updated-action": true }
        };
      });

      it("should successfully update and rename policy with POST and PATCH requests", async () => {
        const reloadSpy = jest.spyOn(service.allPoliciesResource, "reload");

        const savePromise = service.savePolicyEdits(originalPolicy.name, updatedPolicy);

        // Verify optimistic update with new name
        expect(service.allPolicies()[0].name).toBe("renamed-policy");
        expect(service.allPolicies()[0].action).toEqual({ "updated-action": true });

        // Handle POST request for update
        let postReq = httpTestingController.expectOne(`${service.policyBaseUrl}${originalPolicy.name}`);
        expect(postReq.request.method).toBe("POST");
        expect(postReq.request.body).toMatchObject(updatedPolicy);
        postReq.flush(MockPiResponse.fromValue({ status: true }));

        // Give patch request time to be sent after successful POST
        await new Promise(resolve => process.nextTick(resolve));

        // Handle PATCH request for rename
        let patchReq = httpTestingController.expectOne(`${service.policyBaseUrl}${originalPolicy.name}`);
        expect(patchReq.request.method).toBe("PATCH");
        expect(patchReq.request.body).toEqual({ name: "renamed-policy" });
        patchReq.flush(MockPiResponse.fromValue({ status: true }));

        const result = await savePromise;
        expect(result).toBe(true);
        expect(reloadSpy).toHaveBeenCalled();
        expect(notificationService.openSnackBar).toHaveBeenCalledWith(
          expect.stringContaining("Policy updated successfully")
        );
      });

      it("should rollback to original state if POST fails before PATCH", async () => {
        const errorMessage = "Invalid policy data";
        const savePromise = service.savePolicyEdits(originalPolicy.name, updatedPolicy);

        // Verify optimistic update
        expect(service.allPolicies()[0].name).toBe("renamed-policy");

        // Simulate POST failure
        const postReq = httpTestingController.expectOne(`${service.policyBaseUrl}${originalPolicy.name}`);
        postReq.flush({
          result: {
            error: {
              message: errorMessage
            }
          }
        }, { status: 400, statusText: "Bad Request" });

        const result = await savePromise;
        expect(result).toBe(false);
        // Verify rollback - should have original policy with original name
        expect(service.allPolicies()[0].name).toBe("existing-policy");
        expect(service.allPolicies()[0].action).toEqual({ "test-action": true });
        expect(notificationService.openSnackBar).toHaveBeenCalledWith(
          expect.stringContaining("Saving policy failed: " + errorMessage)
        );
      });

      it("should rollback to last stable state if PATCH fails after successful POST", async () => {
        const errorMessage = "Policy name already exists";
        const savePromise = service.savePolicyEdits(originalPolicy.name, updatedPolicy);

        // Handle successful POST request
        const postReq = httpTestingController.expectOne(`${service.policyBaseUrl}${originalPolicy.name}`);
        postReq.flush(MockPiResponse.fromValue({ status: true }));

        // Wait for microtasks to complete
        await new Promise(resolve => process.nextTick(resolve));

        // Handle failed PATCH request
        const patchReq = httpTestingController.expectOne(req => req.method === "PATCH" && req.url === `${service.policyBaseUrl}${originalPolicy.name}`);
        patchReq.flush({
          result: {
            error: {
              message: errorMessage
            }
          }
        }, { status: 409, statusText: "Conflict" });

        const result = await savePromise;
        expect(result).toBe(false);
        // Verify rollback - should have updated action but original name (last stable state after POST)
        expect(service.allPolicies()[0].name).toBe("existing-policy");
        expect(service.allPolicies()[0].action).toEqual({ "updated-action": true });
        expect(notificationService.openSnackBar).toHaveBeenCalledWith(
          expect.stringContaining("Saving policy failed: " + errorMessage)
        );
      });
    });

    describe("Error handling", () => {
      it("should handle unexpected error structure", async () => {
        const savePromise = service.savePolicyEdits(originalPolicy.name, updatedPolicy);

        // Simulate network error
        const postReq = httpTestingController.expectOne(`${service.policyBaseUrl}${originalPolicy.name}`);
        postReq.flush(null, { status: 0, statusText: "Unknown Error" });

        const result = await savePromise;
        expect(result).toBe(false);
        // Verify rollback
        expect(service.allPolicies()[0].action).toEqual({ "test-action": true });
        expect(notificationService.openSnackBar).toHaveBeenCalledWith(
          expect.stringContaining("Saving policy failed")
        );
      });

      it("should handle error without message gracefully", async () => {
        const savePromise = service.savePolicyEdits(originalPolicy.name, updatedPolicy);

        const postReq = httpTestingController.expectOne(`${service.policyBaseUrl}${originalPolicy.name}`);
        postReq.flush({}, { status: 500, statusText: "Internal Server Error" });

        const result = await savePromise;
        expect(result).toBe(false);
        expect(notificationService.openSnackBar).toHaveBeenCalledWith("Saving policy failed");
      });
    });
  });

  describe("allPolicies", () => {

    it("Default should be an empty list", () => {
      expect(service.allPolicies()).toEqual([]);
    });

    it("Should read policies from allPoliciesResource", async () => {
      authService.actionAllowed = jest.fn().mockReturnValue(true);
      contentService.onPolicies = signal(true);
      TestBed.tick();

      const req = httpTestingController.expectOne((r) => r.url === "/policy/");
      expect(req.request.method).toBe("GET");
      const policies = [{
        action: {},
        active: true,
        adminrealm: [],
        adminuser: [],
        check_all_resolvers: false,
        client: [],
        conditions: [],
        description: "Test description",
        name: "Test",
        pinode: [],
        realm: [],
        resolver: [],
        scope: "user",
        time: "",
        user: [],
        user_agents: [],
        user_case_insensitive: false
      }];
      req.flush(MockPiResponse.fromValue(policies));
      await Promise.resolve();

      expect(service.allPolicies()).toEqual(policies);

      httpTestingController.expectOne((r) => r.url === "/policy/defs");
    });

    it("Should handle http error from allPoliciesResource", async () => {
      authService.actionAllowed = jest.fn().mockReturnValue(true);
      contentService.onPolicies = signal(true);
      TestBed.tick();

      const req = httpTestingController.expectOne((r) => r.url === "/policy/");
      expect(req.request.method).toBe("GET");
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403, statusText: "Permission denied"
      });
      await Promise.resolve();

      expect(service.allPolicies()).toEqual([]);

      httpTestingController.expectOne((r) => r.url === "/policy/defs");
    });
  });

  describe("policyActions", () => {

    it("Default should be an empty dict", () => {
      expect(service.policyActions()).toEqual({});
    });

    it("Should read policy actions from policyActionResource", async () => {
      contentService.onPolicies = signal(true);
      TestBed.tick();

      const req = httpTestingController.expectOne((r) => r.url === "/policy/defs");
      expect(req.request.method).toBe("GET");
      const policyActions = {admin: {}, user: {}};
      req.flush(MockPiResponse.fromValue(policyActions));
      await Promise.resolve();

      expect(service.policyActions()).toEqual(policyActions);
    });

    it("Should handle http error from policyActionResource", async () => {
      contentService.onPolicies = signal(true);
      TestBed.tick();

      const req = httpTestingController.expectOne((r) => r.url === "/policy/defs");
      expect(req.request.method).toBe("GET");
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403, statusText: "Permission denied"
      });
      await Promise.resolve();

      expect(service.policyActions()).toEqual({});
      expect(service.allPolicyActionsFlat()).toEqual({});
      expect(service.allPolicyScopes()).toEqual([]);
      expect(service.policyActionsByGroup()).toEqual({});
    });
  });
});
