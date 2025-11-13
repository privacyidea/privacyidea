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

import { Component, computed, inject, input, signal, ViewChild } from "@angular/core";
import { CommonModule } from "@angular/common";
import { AbstractControl, FormControl, FormsModule, ValidationErrors, ReactiveFormsModule } from "@angular/forms";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelect, MatSelectChange, MatSelectModule } from "@angular/material/select";
import { MatButtonModule } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatExpansionModule } from "@angular/material/expansion";
import { PolicyService } from "../../../../../services/policies/policies.service";
import { SystemServiceInterface, SystemService } from "../../../../../services/system/system.service";

@Component({
  selector: "app-conditions-nodes",
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatFormFieldModule,
    MatExpansionModule,
    ReactiveFormsModule
  ],
  templateUrl: "./conditions-nodes.component.html",
  styleUrl: "./conditions-nodes.component.scss"
})
export class ConditionsNodesComponent {
  // ViewChild
  @ViewChild("nodeSelect") nodeSelect!: MatSelect;

  // Services
  policyService: PolicyService = inject(PolicyService);
  systemService: SystemServiceInterface = inject(SystemService);

  // Component State
  isEditMode = this.policyService.isEditMode;
  selectedPolicy = this.policyService.selectedPolicy;

  // Form Controls
  addUserAgentFormControl = new FormControl<string>("", this.userAgentValidator.bind(this));
  validTimeFormControl = new FormControl<string>("", this.validTimeValidator.bind(this));
  clientFormControl = new FormControl<string>("", this.clientValidator.bind(this));

  // Computed Properties
  selectedPolicyName = computed(() => this.selectedPolicy?.name || "");
  availablePinodesList = computed(() => this.systemService.nodes().map((node) => node.name));
  selectedPinodes = computed<string[]>(() => this.selectedPolicy()?.pinode || []);
  selectedUserAgents = computed(() => this.policyService.selectedPolicy()?.user_agents || []);
  selectedValidTime = computed(() => this.policyService.selectedPolicy()?.time || "");
  selectedClient = computed(() => this.policyService.selectedPolicy()?.client || "");
  isAllNodesSelected = computed(() => this.selectedPinodes().length === this.availablePinodesList().length);

  // Placeholder for available user agents
  availableUserAgents = signal<string[]>(["Mozilla Firefox", "Google Chrome", "Microsoft Edge"]);

  constructor() {
    this.validTimeFormControl.valueChanges.subscribe(() => {
      this.setValidTime();
    });

    this.clientFormControl.valueChanges.subscribe(() => {
      this.setClients();
    });
  }

  // Node Selection
  toggleAllNodes() {
    if (this.isAllNodesSelected()) {
      this.policyService.updateSelectedPolicy({ pinode: [] });
    } else {
      this.policyService.updateSelectedPolicy({ pinode: [...this.availablePinodesList()] });
    }
    setTimeout(() => {
      this.nodeSelect.close();
    });
  }

  updateSelectedPinodes($event: MatSelectChange<string[]>) {
    this.policyService.updateSelectedPolicy({ pinode: $event.value });
  }

  // User Agent Management
  addUserAgent() {
    if (this.addUserAgentFormControl.invalid) return;
    const userAgent = this.addUserAgentFormControl.value;
    if (!userAgent) return;
    const oldUserAgents = this.selectedUserAgents();
    if (oldUserAgents.includes(userAgent)) return;
    const newUserAgents = [...oldUserAgents, userAgent];
    this.policyService.updateSelectedPolicy({ user_agents: newUserAgents });
  }

  removeUserAgent(userAgent: string) {
    const newUserAgents = this.selectedUserAgents().filter((ua) => ua !== userAgent);
    this.policyService.updateSelectedPolicy({ user_agents: newUserAgents });
  }

  clearUserAgents() {
    this.policyService.updateSelectedPolicy({ user_agents: [] });
  }

  // Valid Time Management
  setValidTime() {
    if (this.validTimeFormControl.invalid) {
      this.policyService.updateSelectedPolicy({ time: "" });
      return;
    }
    const validTime = this.validTimeFormControl.value;
    if (!validTime) return;
    this.policyService.updateSelectedPolicy({ time: validTime });
  }

  // Client Management
  setClients() {
    if (this.clientFormControl.invalid) {
      this.policyService.updateSelectedPolicy({ client: [] });
      return;
    }
    const client = this.clientFormControl.value;
    if (!client) return;
    const clientsArray = client.split(",").map((c) => c.trim());
    this.policyService.updateSelectedPolicy({ client: clientsArray });
  }

  // Validators
  validTimeValidator(control: AbstractControl): ValidationErrors | null {
    const validTime = control.value;
    if (!validTime) return null;
    const regex =
      /^((Mon|Tue|Wed|Thu|Fri|Sat|Sun)(-(Mon|Tue|Wed|Thu|Fri|Sat|Sun))?:\s([0-1]?[0-9]|2[0-3])-([0-1]?[0-9]|2[0-3])(,\s)?)+$/;
    if (validTime === "" || regex.test(validTime)) {
      return null;
    }
    return { invalidValidTime: { value: control.value } };
  }

  clientValidator(clientControl: AbstractControl<string | null>): ValidationErrors | null {
    const clients = clientControl.value;
    if (!clients) return null;
    if (typeof clients !== "string") return { invalidClient: { value: clientControl.value } };

    const regexIpV4 =
      /^!?(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:\/(?:[0-9]|[12]\d|3[0-2]))?$/;
    const regexIpV6 =
      /^!?(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))(?:\/(?:[0-9]|[1-9]\d|1[01]\d|12[0-8]))?$/;
    const regexHostname =
      /^!?(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9])\.)+([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9-]*[A-Za-z0-9])$/;

    const invalidClients = [];
    const hasLettersRegex = /[a-zA-Z]/;

    for (const client of clients.split(",")) {
      const trimmedClient = client.trim();
      if (trimmedClient.length === 0) continue;
      if (hasLettersRegex.test(trimmedClient)) {
        if (!regexIpV6.test(trimmedClient) && !regexHostname.test(trimmedClient)) {
          invalidClients.push(trimmedClient);
        }
      } else {
        if (!regexIpV4.test(trimmedClient)) {
          invalidClients.push(trimmedClient);
        }
      }
    }

    if (invalidClients.length > 0) {
      return { invalidClient: { value: invalidClients.join(", ") } };
    }
    return null;
  }

  userAgentValidator(control: AbstractControl): ValidationErrors | null {
    const userAgent = control.value;
    if (!userAgent) return null;
    if (userAgent.includes(",")) {
      return { includesComma: { value: control.value } };
    }
    return null;
  }
}
