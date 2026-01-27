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

import { Component, computed, inject, input, output, signal, ViewChild } from "@angular/core";
import { CommonModule } from "@angular/common";
import { AbstractControl, FormControl, FormsModule, ValidationErrors, ReactiveFormsModule } from "@angular/forms";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelect, MatSelectChange, MatSelectModule } from "@angular/material/select";
import { MatButtonModule } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatExpansionModule } from "@angular/material/expansion";
import {
  PolicyService,
  PolicyDetail,
  PolicyServiceInterface
} from "../../../../../../services/policies/policies.service";
import { SystemServiceInterface, SystemService } from "../../../../../../services/system/system.service";
import { MultiSelectOnlyComponent } from "../../../../../shared/multi-select-only/multi-select-only.component";

@Component({
  selector: "app-conditions-environment",
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
    ReactiveFormsModule,
    MultiSelectOnlyComponent
  ],
  templateUrl: "./conditions-environment.component.html",
  styleUrl: "./conditions-environment.component.scss"
})
export class ConditionsEnvironmentComponent {
  // ViewChild
  @ViewChild("nodeSelect") nodeSelect!: MatSelect;
  // Services
  policyService: PolicyServiceInterface = inject(PolicyService);
  systemService: SystemServiceInterface = inject(SystemService);
  // Component State
  isEditMode = input.required<boolean>();
  policy = input.required<PolicyDetail>();
  policyEdit = output<Partial<PolicyDetail>>();
  emitEdits(edits: Partial<PolicyDetail>) {
    this.policyEdit.emit({ ...edits });
  }
  // Form Controls
  addUserAgentFormControl = new FormControl<string>("", this.userAgentValidator.bind(this));
  validTimeFormControl = new FormControl<string>("", this.validTimeValidator.bind(this));
  clientFormControl = new FormControl<string>("", this.clientValidator.bind(this));
  // Computed Properties
  selectedPolicyName = computed(() => this.policy().name);
  availablePinodesList = computed(() => this.systemService.nodes().map((node) => node.name));
  availablePinodesSet = computed(() => new Set(this.availablePinodesList()));
  selectedPinodes = computed<string[]>(() => this.policy().pinode || []);
  selectedUserAgents = computed(() => this.policy().user_agents || []);
  selectedValidTime = computed(() => this.policy().time || "");
  selectedClient = computed(() => this.policy().client || []);
  isAllNodesSelected = computed(() => this.selectedPinodes().length === this.availablePinodesList().length);
  userAgentPresets = [
    "Credential Provider",
    "Keycloak",
    "AD FS",
    "SimpleSAMLphp",
    "PAM",
    "Shibboleth",
    "Nextcloud",
    "FreeRADIUS",
    "LDAP Proxy",
    "privacyIDEA Authenticator",
    "privacyIDEA WebUI"
  ];
  userAgentSearch = signal<string>("");

  filteredUserAgentPresets = computed(() => {
    const selected = this.selectedUserAgents();
    const search = this.userAgentSearch().toLowerCase();

    return this.userAgentPresets.filter((ua) => !selected.includes(ua) && ua.toLowerCase().includes(search));
  });

  // Methode zum Zurücksetzen der Suche beim Schließen/Öffnen
  onDropdownToggled(isOpen: boolean) {
    if (!isOpen) {
      this.userAgentSearch.set("");
    }
  }
  constructor() {
    this.validTimeFormControl.valueChanges.subscribe(() => {
      this.setValidTime();
    });
    this.clientFormControl.valueChanges.subscribe(() => {
      this.setClients();
    });
  }
  ngOnInit() {
    this.validTimeFormControl.setValue(this.policy().time || "");
    this.clientFormControl.setValue(this.policy().client?.join(", ") || "");
  }
  // Node Selection
  toggleAllNodes($event?: MouseEvent) {
    $event?.stopPropagation();
    if (this.isAllNodesSelected()) {
      this.emitEdits({ pinode: [] });
    } else {
      this.emitEdits({ pinode: [...this.availablePinodesList()] });
    }
    setTimeout(() => {
      this.nodeSelect.close();
    });
  }
  selectOnlyThisNode($event: MouseEvent, node: string): void {
    $event.stopPropagation();
    this.emitEdits({ pinode: [node] });
  }
  updateSelectedPinodes($event: string[]) {
    this.emitEdits({ pinode: $event });
  }

  addUserAgentFromSelect($event: MatSelectChange, selectRef: MatSelect) {
    setTimeout(() => {
      selectRef.value = null;
    });
    const userAgent = $event.value;
    if (!userAgent) return;
    const oldUserAgents = this.selectedUserAgents();
    if (oldUserAgents.includes(userAgent)) return;
    const newUserAgents = [...oldUserAgents, userAgent];
    this.emitEdits({ user_agents: newUserAgents });
  }

  // User Agent Management
  addUserAgent() {
    if (this.addUserAgentFormControl.invalid) return;
    const userAgent = this.addUserAgentFormControl.value;
    if (!userAgent) return;
    const oldUserAgents = this.selectedUserAgents();
    if (oldUserAgents.includes(userAgent)) return;
    const newUserAgents = [...oldUserAgents, userAgent];
    this.emitEdits({ user_agents: newUserAgents });
    this.addUserAgentFormControl.setValue("");
  }
  removeUserAgent(userAgent: string) {
    const newUserAgents = this.selectedUserAgents().filter((ua) => ua !== userAgent);
    this.emitEdits({ user_agents: newUserAgents });
  }
  clearUserAgents() {
    this.emitEdits({ user_agents: [] });
  }
  // Valid Time Management
  setValidTime() {
    const validTime = this.validTimeFormControl.value;
    if (this.validTimeFormControl.invalid || !validTime) {
      this.clearValidTime();
      return;
    }
    this.emitEdits({ time: validTime });
  }
  clearValidTimeControl() {
    this.validTimeFormControl.setValue("");
  }
  clearValidTime() {
    this.emitEdits({ time: "" });
  }
  // Client Management
  setClients() {
    const client = this.clientFormControl.value;
    if (this.clientFormControl.invalid || !client) {
      this.clearClients();
      return;
    }
    const clientsArray = client.split(",").map((c) => c.trim());
    this.emitEdits({ client: clientsArray });
  }
  clearClientControl() {
    this.clientFormControl.setValue("");
  }
  clearClients() {
    this.emitEdits({ client: [] });
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

  handleEnterOnSearch(event: Event, select: any): void {
    event.preventDefault();
    event.stopPropagation();

    const currentResults = this.filteredUserAgentPresets();

    if (currentResults.length > 0) {
      const firstMatch = currentResults[0];
      this.addUserAgentFromSelect({ value: firstMatch } as any, select);
      this.userAgentSearch.set("");
      select.close();
    }
  }
}
