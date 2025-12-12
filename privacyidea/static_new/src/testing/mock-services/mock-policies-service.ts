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
import { signal, WritableSignal } from "@angular/core";
import { PiResponse } from "../../app/app.component";
import {
  PolicyActionDetail,
  PolicyDetail,
  PolicyActionGroups,
  PolicyServiceInterface,
  ScopedPolicyActions
} from "../../app/services/policies/policies.service";

export class MockPolicyService implements PolicyServiceInterface {
  isEditMode = signal(false);
  selectedPolicyHasActions = signal(false);
  selectedPolicyHasUserConditions = signal(false);
  selectedPolicyHasNodeConditions = signal(false);
  selectedPolicyHasAdditionalConditions = signal(false);
  selectedPolicyHasConditions = signal(false);
  getEmptyPolicy: PolicyDetail = {
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
  };
  isSelectedPolicyEdited = signal(false);
  selectedPolicy = signal<PolicyDetail | null>(null);
  selectedPolicyOriginal = signal<PolicyDetail | null>(null);
  actionFilter = signal("");
  policyActionGroupNames = signal<string[]>([]);
  selectedActionGroup = signal("");
  selectedAction = signal<{ name: string; value: any } | null>(null);
  policyActions = signal<ScopedPolicyActions>({});
  allPolicyActionsFlat = signal<{ [actionName: string]: PolicyActionDetail }>({});
  allPolicyScopes = signal<string[]>([]);
  policyActionsByGroup = signal<PolicyActionGroups>({});
  alreadyAddedActionNames = signal<string[]>([]);
  policyActionsByGroupFiltered = signal<PolicyActionGroups>({});
  allPolicies = signal<PolicyDetail[]>([]);
  selectedPolicyScope = signal("");
  selectedActionDetail = signal<PolicyActionDetail | null>(null);
  actionNamesOfSelectedGroup = signal<string[]>([]);

  updateActionInSelectedPolicy = jest.fn();
  updateActionValue = jest.fn();
  selectPolicyByName = jest.fn();
  canSaveSelectedPolicy = jest.fn().mockReturnValue(true);
  savePolicyEdits = jest.fn().mockResolvedValue(undefined);
  getDetailsOfAction = jest.fn().mockReturnValue(null);
  deselectNewPolicy = jest.fn();
  deselectPolicy = jest.fn();
  initializeNewPolicy = jest.fn();
  selectPolicy = jest.fn();
  updateSelectedPolicy = jest.fn();
  selectActionByName = jest.fn();
  updateSelectedActionValue = jest.fn();
  createPolicy = jest.fn().mockResolvedValue({} as PiResponse<any>);
  updatePolicy = jest.fn().mockResolvedValue({} as PiResponse<any>);
  deletePolicy = jest.fn().mockResolvedValue({} as PiResponse<number>);
  enablePolicy = jest.fn().mockResolvedValue({} as PiResponse<any>);
  disablePolicy = jest.fn().mockResolvedValue({} as PiResponse<any>);
  addActionToSelectedPolicy = jest.fn();
  removeActionFromSelectedPolicy = jest.fn();
  isScopeChangeable = jest.fn().mockReturnValue(true);
  actionValueIsValid = jest.fn().mockReturnValue(true);
  cancelEditMode = jest.fn();
}
