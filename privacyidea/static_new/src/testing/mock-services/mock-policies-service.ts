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
import { Signal, signal, WritableSignal } from "@angular/core";
import {
  PolicyActionDetail,
  PolicyDetail,
  PolicyActionGroups,
  PolicyServiceInterface,
  ScopedPolicyActions
} from "../../app/services/policies/policies.service";
import { MockHttpResourceRef, MockPiResponse } from "../mock-services";

export class MockPolicyService implements PolicyServiceInterface {
  getEmptyPolicy = jest.fn().mockReturnValue({
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
  isEditMode: Signal<boolean> = signal(false);
  policyActions: Signal<ScopedPolicyActions> = signal({});
  allPolicyActionsFlat: Signal<{ [actionName: string]: PolicyActionDetail }> = signal({});
  allPolicyScopes: Signal<string[]> = signal([]);
  policyActionsByGroup: Signal<PolicyActionGroups> = signal({});
  filteredPolicyActionGroups = jest.fn().mockReturnValue({});
  getActionDetail = jest.fn().mockReturnValue(null);
  getGroupOfAction = jest.fn().mockReturnValue(null);
  getScopeOfAction = jest.fn().mockReturnValue(null);
  allPolicies: WritableSignal<PolicyDetail[]> = signal([]);
  canSavePolicy = jest.fn().mockReturnValue(true);
  getDetailsOfAction = jest.fn().mockReturnValue(null);
  copyPolicy = jest.fn().mockResolvedValue(MockPiResponse.fromValue({}));
  createPolicy = jest.fn().mockResolvedValue(MockPiResponse.fromValue({}));
  updatePolicy = jest.fn().mockResolvedValue(MockPiResponse.fromValue({}));
  deletePolicy = jest.fn().mockResolvedValue(MockPiResponse.fromValue(1));
  enablePolicy = jest.fn().mockResolvedValue(MockPiResponse.fromValue({}));
  disablePolicy = jest.fn().mockResolvedValue(MockPiResponse.fromValue({}));
  isScopeChangeable = jest.fn().mockReturnValue(true);
  getActionNamesOf = jest.fn().mockReturnValue([]);
  getActionsOf = jest.fn().mockReturnValue({});
  actionValueIsValid = jest.fn().mockReturnValue(true);
  saveNewPolicy = jest.fn().mockResolvedValue(undefined);
  policyHasConditions = jest.fn().mockReturnValue(true);
  policyHasAdminConditions = jest.fn().mockReturnValue(true);
  policyHasUserConditions = jest.fn().mockReturnValue(true);
  policyHasEnviromentConditions = jest.fn().mockReturnValue(true);
  policyHasAdditionalConditions = jest.fn().mockReturnValue(true);
  policyHasActions = jest.fn().mockReturnValue(true);
  savePolicyEdits = jest.fn().mockReturnValue(undefined);
  isPolicyEdited = jest.fn().mockReturnValue(true);
  togglePolicyActive = jest.fn().mockReturnValue(undefined);
  updatePolicyOptimistic = jest.fn().mockReturnValue(undefined);
  allPoliciesRecource = new MockHttpResourceRef(undefined);
}
