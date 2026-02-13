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
import { PolicyService, PolicyDetail, PolicyActionDetail } from "./policies.service";
import { AuthService } from "../auth/auth.service";
import { ContentService } from "../content/content.service";
import { MockContentService, MockPiResponse } from "src/testing/mock-services";
import { MockAuthService } from "src/testing/mock-services/mock-auth-service";

describe("PolicyService", () => {
  let service: PolicyService;
  let httpTestingController: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        PolicyService,
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService }
      ]
    });
    service = TestBed.inject(PolicyService);
    httpTestingController = TestBed.inject(HttpTestingController);
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
      expect(service.policyHasEnviromentConditions(policy)).toBeTruthy();
    });
    it("should detect additional conditions", () => {
      const policy = service.getEmptyPolicy();
      policy.conditions = [["userinfo", "key", "equals", "value", false, "raise_error"]];
      expect(service.policyHasAdditionalConditions(policy)).toBeTruthy();
    });
  });
  describe("HTTP Actions & Signals", () => {
    it("should send a POST request when saving policy edits (optimistic update)", () => {
      const policy = service.getEmptyPolicy();
      policy.name = "test-policy";
      service.allPolicies.set([policy]);
      service.savePolicyEdits("test-policy", { description: "updated" });
      const req = httpTestingController.expectOne(`${service.policyBaseUrl}test-policy`);
      expect(req.request.method).toBe("POST");
      expect(req.request.body.description).toBe("updated");
      req.flush(MockPiResponse.fromValue({}));
    });
    it("should toggle policy active state optimistically", () => {
      const policy: PolicyDetail = { ...service.getEmptyPolicy(), name: "test", active: true };
      service.allPolicies.set([policy]);
      service.togglePolicyActive(policy);
      expect(service.allPolicies()[0].active).toBeFalsy();
      const req = httpTestingController.expectOne(`${service.policyBaseUrl}disable/test`);
      req.flush(MockPiResponse.fromValue({}));
    });
    it("should delete a policy and update the signal", async () => {
      const policy = { ...service.getEmptyPolicy(), name: "to-delete" };
      service.allPolicies.set([policy]);
      const deletePromise = service.deletePolicy("to-delete");
      const req = httpTestingController.expectOne(`${service.policyBaseUrl}to-delete`);
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
});
