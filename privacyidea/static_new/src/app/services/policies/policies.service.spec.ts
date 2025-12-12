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
import { PolicyActionDetail, PolicyDetail, PolicyService, ScopedPolicyActions } from "./policies.service";
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { MockLocalService, MockNotificationService, MockPiResponse } from "../../../testing/mock-services";

describe("PolicyService", () => {
  let service: PolicyService;
  let httpTestingController: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),

        { provide: MockLocalService },
        { provide: MockNotificationService }
      ]
    });
    service = TestBed.inject(PolicyService);

    httpTestingController = TestBed.inject(HttpTestingController);
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("should have an empty policy defined", () => {
    expect(service.getEmptyPolicy).toEqual({
      action: null,
      active: true,
      adminrealm: [],
      adminuser: [],
      check_all_resolvers: false,
      client: [],
      conditions: [],
      description: null,
      name: "",
      pinode: [],
      priority: 1,
      realm: [],
      resolver: [],
      scope: "",
      time: "",
      user: [],
      user_agents: [],
      user_case_insensitive: false
    });
  });

  it("should initialize a new policy", () => {
    service.initializeNewPolicy();
    expect(service.selectedPolicy()).toEqual(service.getEmptyPolicy);
    expect(service.selectedPolicyOriginal()).toEqual(service.getEmptyPolicy);
  });

  it("should select a policy", () => {
    const policy: PolicyDetail = { ...service.getEmptyPolicy, name: "test-policy" };
    service.selectPolicy(policy);
    expect(service.selectedPolicy()).toEqual(policy);
    expect(service.selectedPolicyOriginal()).toEqual(policy);
  });

  it("should deselect a policy", () => {
    const policy: PolicyDetail = { ...service.getEmptyPolicy, name: "test-policy" };
    service.selectPolicy(policy);
    service.deselectPolicy("test-policy");
    expect(service.selectedPolicy()).toBeNull();
    expect(service.selectedPolicyOriginal()).toBeNull();
  });

  it("should not deselect a policy if name does not match", () => {
    const policy: PolicyDetail = { ...service.getEmptyPolicy, name: "test-policy" };
    service.selectPolicy(policy);
    service.deselectPolicy("other-policy");
    expect(service.selectedPolicy()).toEqual(policy);
    expect(service.selectedPolicyOriginal()).toEqual(policy);
  });

  it("should deselect a new policy", () => {
    service.initializeNewPolicy();
    service.deselectNewPolicy();
    expect(service.selectedPolicy()).toBeNull();
    expect(service.selectedPolicyOriginal()).toBeNull();
  });

  it("should update selected policy", () => {
    const policy: PolicyDetail = { ...service.getEmptyPolicy, name: "test-policy" };
    service.selectPolicy(policy);
    service.updateSelectedPolicy({ description: "new description" });
    expect(service.selectedPolicy()?.description).toBe("new description");
    expect(service.selectedPolicyOriginal()?.description).toBeNull(); // Original should not change
  });

  describe("isPolicyEdited", () => {
    it("should return false if no policy is selected", () => {
      expect(service.isSelectedPolicyEdited()).toBeFalsy();
    });

    it("should return false if policy is not edited", () => {
      const policy: PolicyDetail = { ...service.getEmptyPolicy, name: "test-policy" };
      service.selectPolicy(policy);
      expect(service.isSelectedPolicyEdited()).toBeFalsy();
    });

    it("should return true if policy is edited", () => {
      const policy: PolicyDetail = { ...service.getEmptyPolicy, name: "test-policy" };
      service.selectPolicy(policy);
      service.updateSelectedPolicy({ description: "new description" });
      expect(service.isSelectedPolicyEdited()).toBeTruthy();
    });

    it("should return true if new policy is edited", () => {
      service.initializeNewPolicy();
      service.updateSelectedPolicy({ name: "new-policy" });
      expect(service.isSelectedPolicyEdited()).toBeTruthy();
    });

    it("should return false if new policy is not edited (only scope changed)", () => {
      service.initializeNewPolicy();
      service.updateSelectedPolicy({ scope: "user" });
      expect(service.isSelectedPolicyEdited()).toBeFalsy();
    });
  });

  describe("canSaveSelectedPolicy", () => {
    it("should return false if no policy is selected", () => {
      expect(service.canSaveSelectedPolicy()).toBeFalsy();
    });

    it("should return false if policy name is empty", () => {
      service.selectPolicy({ ...service.getEmptyPolicy, name: "", scope: "user", action: { test: "test" } });
      expect(service.canSaveSelectedPolicy()).toBeFalsy();
    });

    it("should return false if policy scope is empty", () => {
      service.selectPolicy({ ...service.getEmptyPolicy, name: "test", scope: "", action: { test: "test" } });
      expect(service.canSaveSelectedPolicy()).toBeFalsy();
    });

    it("should return false if policy has no actions", () => {
      service.selectPolicy({ ...service.getEmptyPolicy, name: "test", scope: "user", action: null });
      expect(service.canSaveSelectedPolicy()).toBeFalsy();
    });

    it("should return true if policy is valid", () => {
      service.selectPolicy({ ...service.getEmptyPolicy, name: "test", scope: "user", action: { test: "test" } });
      expect(service.canSaveSelectedPolicy()).toBeTruthy();
    });
  });

  describe("selectedPolicyHasActions", () => {
    it("should return false if no policy is selected", () => {
      expect(service.selectedPolicyHasActions()).toBeFalsy();
    });

    it("should return false if policy has no actions", () => {
      service.selectPolicy({ ...service.getEmptyPolicy, action: null });
      expect(service.selectedPolicyHasActions()).toBeFalsy();
    });

    it("should return true if policy has actions", () => {
      service.selectPolicy({ ...service.getEmptyPolicy, action: { test: "test" } });
      expect(service.selectedPolicyHasActions()).toBeTruthy();
    });
  });

  describe("selectedPolicyHasUserConditions", () => {
    it("should return false if no policy is selected", () => {
      expect(service.selectedPolicyHasUserConditions()).toBeFalsy();
    });

    it("should return true if policy has realms", () => {
      service.selectPolicy({ ...service.getEmptyPolicy, realm: ["test"] });
      expect(service.selectedPolicyHasUserConditions()).toBeTruthy();
    });

    it("should return true if policy has resolvers", () => {
      service.selectPolicy({ ...service.getEmptyPolicy, resolver: ["test"] });
      expect(service.selectedPolicyHasUserConditions()).toBeTruthy();
    });

    it("should return true if policy has users", () => {
      service.selectPolicy({ ...service.getEmptyPolicy, user: ["test"] });
      expect(service.selectedPolicyHasUserConditions()).toBeTruthy();
    });

    it("should return false if policy has no user conditions", () => {
      service.selectPolicy(service.getEmptyPolicy);
      expect(service.selectedPolicyHasUserConditions()).toBeFalsy();
    });
  });

  describe("selectedPolicyHasNodeConditions", () => {
    it("should return false if no policy is selected", () => {
      expect(service.selectedPolicyHasNodeConditions()).toBeFalsy();
    });

    it("should return true if policy has pinodes", () => {
      service.selectPolicy({ ...service.getEmptyPolicy, pinode: ["test"] });
      expect(service.selectedPolicyHasNodeConditions()).toBeTruthy();
    });

    it("should return true if policy has time", () => {
      service.selectPolicy({ ...service.getEmptyPolicy, time: "test" });
      expect(service.selectedPolicyHasNodeConditions()).toBeTruthy();
    });

    it("should return true if policy has client", () => {
      service.selectPolicy({ ...service.getEmptyPolicy, client: ["test"] });
      expect(service.selectedPolicyHasNodeConditions()).toBeTruthy();
    });

    it("should return true if policy has user agents", () => {
      service.selectPolicy({ ...service.getEmptyPolicy, user_agents: ["test"] });
      expect(service.selectedPolicyHasNodeConditions()).toBeTruthy();
    });

    it("should return false if policy has no node conditions", () => {
      service.selectPolicy(service.getEmptyPolicy);
      expect(service.selectedPolicyHasNodeConditions()).toBeFalsy();
    });
  });

  describe("selectedPolicyHasAdditionalConditions", () => {
    it("should return false if no policy is selected", () => {
      expect(service.selectedPolicyHasAdditionalConditions()).toBeFalsy();
    });

    it("should return true if policy has additional conditions", () => {
      service.selectPolicy({
        ...service.getEmptyPolicy,
        conditions: [["userinfo", "key", "!contains", "value", false, "condition_is_false"]]
      });
      expect(service.selectedPolicyHasAdditionalConditions()).toBeTruthy();
    });

    it("should return false if policy has no additional conditions", () => {
      service.selectPolicy(service.getEmptyPolicy);
      expect(service.selectedPolicyHasAdditionalConditions()).toBeFalsy();
    });
  });

  describe("selectedPolicyHasConditions", () => {
    it("should return false if no policy is selected", () => {
      expect(service.selectedPolicyHasConditions()).toBeFalsy();
    });

    it("should return true if policy has user conditions", () => {
      service.selectPolicy({ ...service.getEmptyPolicy, realm: ["test"] });
      expect(service.selectedPolicyHasConditions()).toBeTruthy();
    });

    it("should return true if policy has node conditions", () => {
      service.selectPolicy({ ...service.getEmptyPolicy, pinode: ["test"] });
      expect(service.selectedPolicyHasConditions()).toBeTruthy();
    });

    it("should return true if policy has additional conditions", () => {
      service.selectPolicy({
        ...service.getEmptyPolicy,
        conditions: [["userinfo", "key", "!contains", "value", false, "condition_is_false"]]
      });
      expect(service.selectedPolicyHasConditions()).toBeTruthy();
    });

    it("should return false if policy has no conditions", () => {
      service.selectPolicy(service.getEmptyPolicy);
      expect(service.selectedPolicyHasConditions()).toBeFalsy();
    });
  });

  describe("savePolicyEdits", () => {
    it("should create a new policy if asNew is true", () => {
      service.initializeNewPolicy();
      service.updateSelectedPolicy({ name: "new-policy", scope: "user", action: { test: "test" } });
      const savePromise = service.savePolicyEditsAsNew();

      const req = httpTestingController.expectOne(`${service.policyBaseUrl}new-policy`);
      expect(req.request.method).toEqual("POST");
      req.flush({ result: { value: {} } });
    });

    it("should update an existing policy if asNew is false", () => {
      const policy: PolicyDetail = {
        ...service.getEmptyPolicy,
        name: "test-policy",
        scope: "user",
        action: { test: "test" }
      };
      service.selectPolicy(policy);
      service.updateSelectedPolicy({ description: "updated description" });
      service.savePolicyEdits();

      const req = httpTestingController.expectOne(`${service.policyBaseUrl}test-policy`);
      expect(req.request.method).toEqual("POST");
      req.flush({ result: { value: {} } });
    });
  });

  describe("createPolicy", () => {
    it("should send a POST request to create a policy", () => {
      const policyData: PolicyDetail = { ...service.getEmptyPolicy, name: "new-policy" };
      service.createPolicy(policyData).then();

      const req = httpTestingController.expectOne(`${service.policyBaseUrl}new-policy`);
      expect(req.request.method).toEqual("POST");
      req.flush({ result: { value: {} } });
    });
  });

  describe("updatePolicy", () => {
    it("should send a POST request to update a policy", async () => {
      const policyData: PolicyDetail = { ...service.getEmptyPolicy, name: "updated-policy" };
      const promise = service.updatePolicy("updated-policy", policyData);

      const req = httpTestingController.expectOne(`${service.policyBaseUrl}updated-policy`);
      expect(req.request.method).toEqual("POST");
      expect(req.request.body).toEqual(policyData);
      req.flush({ result: { value: {} } });

      await promise;
    });

    it("should send a PATCH and a POST request if policy name changes", () => {
      const policyData: PolicyDetail = { ...service.getEmptyPolicy, name: "new-name" };

      service.updatePolicy("old-name", policyData);

      const reqPatch = httpTestingController.expectOne(`${service.policyBaseUrl}old-name`);
      expect(reqPatch.request.method).toEqual("PATCH");
      expect(reqPatch.request.body).toEqual({ name: "new-name" });
      reqPatch.flush({ result: { value: {} } });

      const reqPost = httpTestingController.expectOne(`${service.policyBaseUrl}new-name`);
      expect(reqPost.request.method).toEqual("POST");
      expect(reqPost.request.body).toEqual(policyData);
      reqPost.flush({ result: { value: {} } });

      httpTestingController.verify();
    });
  });

  describe("deletePolicy", () => {
    it("should send a DELETE request to delete a policy", () => {
      const policy: PolicyDetail = { ...service.getEmptyPolicy, name: "test-policy" };
      service.allPolicies.set([policy]);
      service.deletePolicy("test-policy").then();

      const req = httpTestingController.expectOne(`${service.policyBaseUrl}test-policy`);
      expect(req.request.method).toEqual("DELETE");
      req.flush({ result: { value: 1 } });
    });

    it("should reject if policy not found", async () => {
      await service.deletePolicy("non-existent").catch((e) => {
        expect(e).toEqual("Policy with name non-existent not found");
      });
    });
  });

  describe("enablePolicy", () => {
    it("should send a POST request to enable a policy", () => {
      service.enablePolicy("test-policy").then();

      const req = httpTestingController.expectOne(`${service.policyBaseUrl}enable/test-policy`);
      expect(req.request.method).toEqual("POST");
      req.flush({ result: { value: {} } });
    });
  });

  describe("disablePolicy", () => {
    it("should send a POST request to disable a policy", () => {
      service.disablePolicy("test-policy").then();

      const req = httpTestingController.expectOne(`${service.policyBaseUrl}disable/test-policy`);
      expect(req.request.method).toEqual("POST");
      req.flush({ result: { value: {} } });
    });
  });

  describe("getDetailsOfAction", () => {
    it("should return action details for a given action name", () => {
      service.policyActionResource.set(MockPiResponse.fromValue({ user: { test: { type: "str", desc: "test" } } }));
      service.selectPolicy({ ...service.getEmptyPolicy, scope: "user" });
      expect(service.getDetailsOfAction("test")).toEqual({ type: "str", desc: "test" });
    });

    it("should return null if action not found", () => {
      service.policyActionResource.set(MockPiResponse.fromValue({ user: { test: { type: "str", desc: "test" } } }));
      service.selectPolicy({ ...service.getEmptyPolicy, scope: "user" });
      expect(service.getDetailsOfAction("non-existent")).toBeNull();
    });
  });

  describe("isScopeChangeable", () => {
    it("should return true if policy has no actions", () => {
      const policy: PolicyDetail = { ...service.getEmptyPolicy, action: null };
      expect(service.isScopeChangeable(policy)).toBeTruthy();
    });

    it("should return false if policy has actions", () => {
      const policy: PolicyDetail = { ...service.getEmptyPolicy, action: { test: "test" } };
      expect(service.isScopeChangeable(policy)).toBeFalsy();
    });
  });

  describe("getActionNamesOfSelectedGroup", () => {
    it("should return action names of selected group", () => {
      const asd: PolicyActionDetail = { type: "str", desc: "test" };
      const mock = MockPiResponse.fromValue<ScopedPolicyActions, unknown>({
        scope1: {
          action1: {
            type: "str",
            desc: "test",
            group: "group1"
          },
          action2: {
            type: "bool",
            desc: "test2",
            group: "group2"
          }
        }
      });
      service.policyActionResource.set(mock);
      service.selectPolicy({ ...service.getEmptyPolicy, scope: "scope1" });
      service.selectedActionGroup.set("group1");
      expect(service.actionNamesOfSelectedGroup()).toEqual(["action1"]);
    });

    it("should return empty array if no scope selected", () => {
      service.policyActionResource.set(MockPiResponse.fromValue({ user: { test: { type: "str", desc: "test" } } }));
      service.selectedActionGroup.set("group1");
      expect(service.actionNamesOfSelectedGroup()).toEqual([]);
    });
  });

  describe("actionValueIsValid", () => {
    it("should validate boolean action correctly", () => {
      const action: PolicyActionDetail = { desc: "", type: "bool" };
      expect(service.actionValueIsValid(action, "true")).toBeTruthy();
      expect(service.actionValueIsValid(action, "false")).toBeTruthy();
      expect(service.actionValueIsValid(action, "invalid")).toBeFalsy();
    });

    it("should validate integer action correctly", () => {
      const action: PolicyActionDetail = { desc: "", type: "int" };
      expect(service.actionValueIsValid(action, "123")).toBeTruthy();
      expect(service.actionValueIsValid(action, "-123")).toBeTruthy();
      expect(service.actionValueIsValid(action, "12.3")).toBeFalsy();
      expect(service.actionValueIsValid(action, "invalid")).toBeFalsy();
    });

    it("should validate string action correctly", () => {
      const action: PolicyActionDetail = { desc: "", type: "str" };
      expect(service.actionValueIsValid(action, "test")).toBeTruthy();
      expect(service.actionValueIsValid(action, "")).toBeFalsy();
    });

    it("should validate text action correctly", () => {
      const action: PolicyActionDetail = { desc: "", type: "text" };
      expect(service.actionValueIsValid(action, "test")).toBeTruthy();
      expect(service.actionValueIsValid(action, "")).toBeFalsy();
    });
  });

  describe("cancelEditMode", () => {
    it("should revert selected policy to original", () => {
      const originalPolicy: PolicyDetail = { ...service.getEmptyPolicy, name: "original" };
      const editedPolicy: PolicyDetail = { ...service.getEmptyPolicy, name: "edited" };
      service.selectPolicy(originalPolicy);
      service.updateSelectedPolicy({ name: "edited" });
      service.cancelEditMode();
      expect(service.selectedPolicy()).not.toEqual(editedPolicy);
      expect(service.selectedPolicy()).toEqual(originalPolicy);
    });
  });
});
