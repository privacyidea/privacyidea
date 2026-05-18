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

import { Component, computed, effect, inject, input, OnInit, output, signal, ViewChild } from "@angular/core";

import { form, FormField, validate } from "@angular/forms/signals";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelect, MatSelectChange, MatSelectModule } from "@angular/material/select";
import { ClearButtonComponent } from "@components/shared/clear-button/clear-button.component";
import { MultiSelectOnlyComponent } from "@components/shared/multi-select-only/multi-select-only.component";
import { PolicyDetail, PolicyService, PolicyServiceInterface } from "@services/policies/policies.service";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";

@Component({
  selector: "app-edit-environment-conditions",
  standalone: true,
  imports: [
    FormField,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatFormFieldModule,
    MatExpansionModule,
    MultiSelectOnlyComponent,
    ClearButtonComponent,
    MatAutocompleteModule
  ],
  templateUrl: "./edit-environment-conditions.component.html",
  styleUrl: "./edit-environment-conditions.component.scss"
})
export class EditEnvironmentConditionsComponent implements OnInit {
  @ViewChild("nodeSelect") nodeSelect!: MatSelect;

  readonly policyService: PolicyServiceInterface = inject(PolicyService);
  readonly systemService: SystemServiceInterface = inject(SystemService);

  readonly policy = input.required<PolicyDetail>();
  readonly policyEdit = output<Partial<PolicyDetail>>();

  readonly addUserAgentSignal = signal("");
  readonly addUserAgentField = form(this.addUserAgentSignal, (f) => {
    validate(f, (ctx) => { const value = ctx.value(); return value && value.includes(",") ? [{ kind: "includesComma" }] : []; });
  });

  readonly validTimeSignal = signal("");
  readonly validTimeField = form(this.validTimeSignal, (f) => {
    validate(f, (ctx) => {
      const value = ctx.value();
      if (!value) return [];
      const regex =
        /^((Mon|Tue|Wed|Thu|Fri|Sat|Sun)(-(Mon|Tue|Wed|Thu|Fri|Sat|Sun))?:\s([0-1]?[0-9]|2[0-3])-([0-1]?[0-9]|2[0-3])(,\s)?)+$/;
      return regex.test(value) ? [] : [{ kind: "invalidValidTime" }];
    });
  });

  readonly clientSignal = signal("");
  readonly clientField = form(this.clientSignal, (f) => {
    validate(f, (ctx) => {
      const value = ctx.value();
      if (!value) return [];
      const regexIpV4 =
        /^!?(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:\/(?:[0-9]|[12]\d|3[0-2]))?$/;
      const regexIpV6 =
        /^!?(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))(?:\/(?:[0-9]|[1-9]\d|1[01]\d|12[0-8]))?$/;
      const regexHostname =
        /^!?(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9])\.)+([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9-]*[A-Za-z0-9])$/;
      const invalidClients = value
        .split(",")
        .map((c: string) => c.trim())
        .filter((c: string) => c !== "")
        .filter((c: string) => !regexIpV4.test(c) && !regexIpV6.test(c) && !regexHostname.test(c));
      return invalidClients.length > 0 ? [{ kind: "invalidClient" }] : [];
    });
  });

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

  readonly availablePinodesList = computed(() => this.systemService.nodes().map((node) => node.name));
  readonly selectedPinodes = computed<string[]>(() => this.policy().pinode || []);
  readonly selectedUserAgents = computed(() => this.policy().user_agents || []);

  filteredUserAgentPresets = computed(() => {
    const selected = this.selectedUserAgents();
    const search = this.userAgentSearch().toLowerCase();
    return this.userAgentPresets.filter((ua) => !selected.includes(ua) && ua.toLowerCase().includes(search));
  });

  constructor() {
    effect(() => {
      const value = this.validTimeSignal();
      if (this.validTimeField().errors().length === 0) {
        this.emitEdits({ time: value || "" });
      }
    });
    effect(() => {
      const value = this.clientSignal();
      if (this.clientField().errors().length === 0) {
        const clientsArray = value
          ? value.split(",").map((c) => c.trim()).filter((c) => c !== "")
          : [];
        this.emitEdits({ client: clientsArray });
      }
    });
  }

  ngOnInit() {
    this.validTimeSignal.set(this.policy().time || "");
    this.clientSignal.set(this.policy().client?.join(", ") || "");
  }

  emitEdits(edits: Partial<PolicyDetail>) {
    this.policyEdit.emit(edits);
  }

  updateSelectedPinodes($event: string[]) {
    this.emitEdits({ pinode: $event });
  }

  addUserAgentFromSelect($event: MatSelectChange, selectRef: MatSelect) {
    const userAgent = $event.value;
    if (!userAgent) return;
    const oldUserAgents = this.selectedUserAgents();
    if (!oldUserAgents.includes(userAgent)) {
      this.emitEdits({ user_agents: [...oldUserAgents, userAgent] });
    }
    setTimeout(() => (selectRef.value = null));
  }

  addUserAgent() {
    const userAgent = this.addUserAgentSignal()?.trim();
    if (this.addUserAgentField().errors().length > 0 || !userAgent) return;
    const oldUserAgents = this.selectedUserAgents();
    if (!oldUserAgents.includes(userAgent)) {
      this.emitEdits({ user_agents: [...oldUserAgents, userAgent] });
    }
    this.addUserAgentSignal.set("");
  }

  removeUserAgent(userAgent: string) {
    this.emitEdits({ user_agents: this.selectedUserAgents().filter((ua) => ua !== userAgent) });
  }

  clearUserAgents() {
    this.emitEdits({ user_agents: [] });
  }

  clearValidTimeControl() {
    this.validTimeSignal.set("");
  }

  clearClientControl() {
    this.clientSignal.set("");
  }

  handleEnterOnSearch(event: Event, select: any): void {
    event.preventDefault();
    event.stopPropagation();
    const currentResults = this.filteredUserAgentPresets();
    if (currentResults.length > 0) {
      this.addUserAgentFromSelect({ value: currentResults[0] } as any, select);
      this.userAgentSearch.set("");
      select.close();
    }
  }
}
