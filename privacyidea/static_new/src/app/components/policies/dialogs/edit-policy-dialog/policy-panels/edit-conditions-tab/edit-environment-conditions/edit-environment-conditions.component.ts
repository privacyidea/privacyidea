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

import { Component, computed, inject, input, OnInit, output, signal, ViewChild } from "@angular/core";

import { toSignal } from "@angular/core/rxjs-interop";
import { AbstractControl, FormControl, FormsModule, ReactiveFormsModule, ValidationErrors } from "@angular/forms";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelect, MatSelectChange, MatSelectModule } from "@angular/material/select";
import { ClearButtonComponent } from "@components/shared/clear-button/clear-button.component";
import { MultiSelectOnlyComponent } from "@components/shared/multi-select-only/multi-select-only.component";
import { ClientsService, ClientsServiceInterface } from "@services/clients/clients.service";
import { PolicyDetail, PolicyService, PolicyServiceInterface } from "@services/policies/policies.service";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";

interface ClientSuggestion {
  ip: string;
  hostname?: string;
  applications: string[];
}

@Component({
  selector: "app-edit-environment-conditions",
  standalone: true,
  imports: [
    FormsModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatFormFieldModule,
    MatExpansionModule,
    ReactiveFormsModule,
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
  readonly clientsService: ClientsServiceInterface = inject(ClientsService);

  readonly policy = input.required<PolicyDetail>();
  readonly policyEdit = output<Partial<PolicyDetail>>();

  addUserAgentFormControl = new FormControl<string>("", this.userAgentValidator.bind(this));
  validTimeFormControl = new FormControl<string>("", this.validTimeValidator.bind(this));
  clientFormControl = new FormControl<string>("", this.clientValidator.bind(this));
  private readonly clientControlValue = toSignal(this.clientFormControl.valueChanges, {
    initialValue: this.clientFormControl.value
  });

  readonly knownClients = computed<ClientSuggestion[]>(() => {
    const dict = this.clientsService.clientsResource.value()?.result?.value ?? {};
    const map = new Map<string, ClientSuggestion>();
    for (const application of Object.keys(dict)) {
      for (const cd of dict[application]) {
        if (!cd.ip) continue;
        let entry = map.get(cd.ip);
        if (!entry) {
          entry = { ip: cd.ip, hostname: cd.hostname ?? undefined, applications: [] };
          map.set(cd.ip, entry);
        }
        if (cd.hostname && !entry.hostname) entry.hostname = cd.hostname;
        if (!entry.applications.includes(application)) entry.applications.push(application);
      }
    }
    return Array.from(map.values()).sort((a, b) => a.ip.localeCompare(b.ip));
  });

  readonly clientSearchTerm = computed<string>(() => {
    const segment = this.currentClientSegment(this.clientControlValue() ?? "").raw;
    return segment.trim().replace(/^!\s*/, "").toLowerCase();
  });

  readonly filteredKnownClients = computed<ClientSuggestion[]>(() => {
    const term = this.clientSearchTerm();
    const clients = this.knownClients();
    const matches = term
      ? clients.filter(
          (c) =>
            c.ip.toLowerCase().includes(term) ||
            (c.hostname ?? "").toLowerCase().includes(term) ||
            c.applications.some((app) => app.toLowerCase().includes(term))
        )
      : clients;
    return matches.slice(0, 20);
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
    this.validTimeFormControl.valueChanges.subscribe(() => this.setValidTime());
    this.clientFormControl.valueChanges.subscribe(() => this.setClients());
  }

  ngOnInit() {
    this.validTimeFormControl.setValue(this.policy().time || "", { emitEvent: false });
    this.clientFormControl.setValue(this.policy().client?.join(", ") || "", { emitEvent: false });
    this.clientsService.requestClientsForAutocomplete();
  }

  private currentClientSegment(value: string): { before: string; raw: string } {
    const idx = value.lastIndexOf(",");
    if (idx === -1) return { before: "", raw: value };
    return { before: value.slice(0, idx + 1), raw: value.slice(idx + 1) };
  }

  buildClientSelection(ip: string): string {
    const value = this.clientFormControl.value ?? "";
    const { before, raw } = this.currentClientSegment(value);
    const prefixMatch = raw.match(/^(\s*!?)/);
    const prefix = prefixMatch ? prefixMatch[1] : "";
    const leadingSpace = before && !prefix.startsWith(" ") ? " " : "";
    return `${before}${leadingSpace}${prefix.replace(/^\s+/, "")}${ip}`;
  }

  formatClientSuggestion(c: ClientSuggestion): string {
    const host = c.hostname ? ` — ${c.hostname}` : "";
    const apps = c.applications.length ? ` (${c.applications.join(", ")})` : "";
    return `${c.ip}${host}${apps}`;
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
    const userAgent = this.addUserAgentFormControl.value?.trim();
    if (this.addUserAgentFormControl.invalid || !userAgent) return;
    const oldUserAgents = this.selectedUserAgents();
    if (!oldUserAgents.includes(userAgent)) {
      this.emitEdits({ user_agents: [...oldUserAgents, userAgent] });
    }
    this.addUserAgentFormControl.setValue("");
  }

  removeUserAgent(userAgent: string) {
    this.emitEdits({ user_agents: this.selectedUserAgents().filter((ua) => ua !== userAgent) });
  }

  clearUserAgents() {
    this.emitEdits({ user_agents: [] });
  }

  setValidTime() {
    const validTime = this.validTimeFormControl.value;
    if (this.validTimeFormControl.valid) {
      this.emitEdits({ time: validTime || "" });
    }
  }

  clearValidTimeControl() {
    this.validTimeFormControl.setValue("");
  }

  setClients() {
    const client = this.clientFormControl.value;
    if (this.clientFormControl.valid) {
      const clientsArray = client
        ? client
            .split(",")
            .map((c) => c.trim())
            .filter((c) => c !== "")
        : [];
      this.emitEdits({ client: clientsArray });
    }
  }

  clearClientControl() {
    this.clientFormControl.setValue("");
  }

  validTimeValidator(control: AbstractControl): ValidationErrors | null {
    const validTime = control.value;
    if (!validTime) return null;
    const regex =
      /^((Mon|Tue|Wed|Thu|Fri|Sat|Sun)(-(Mon|Tue|Wed|Thu|Fri|Sat|Sun))?:\s([0-1]?[0-9]|2[0-3])-([0-1]?[0-9]|2[0-3])(,\s)?)+$/;
    return regex.test(validTime) ? null : { invalidValidTime: { value: control.value } };
  }
  readonly regexIpV4 =
    /^!?(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:\/(?:[0-9]|[12]\d|3[0-2]))?$/;
  readonly regexIpV6 =
    /^!?(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))(?:\/(?:[0-9]|[1-9]\d|1[01]\d|12[0-8]))?$/;
  readonly regexHostname =
    /^!?(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9])\.)+([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9-]*[A-Za-z0-9])$/;

  clientValidator(clientControl: AbstractControl<string | null>): ValidationErrors | null {
    const clients = clientControl.value;
    if (!clients) return null;
    const invalidClients = clients
      .split(",")
      .map((c) => c.trim())
      .filter((c) => c !== "")
      .filter((c) => !this.regexIpV4.test(c) && !this.regexIpV6.test(c) && !this.regexHostname.test(c));
    return invalidClients.length > 0 ? { invalidClient: { value: invalidClients.join(", ") } } : null;
  }

  userAgentValidator(control: AbstractControl): ValidationErrors | null {
    const userAgent = control.value;
    return userAgent && userAgent.includes(",") ? { includesComma: { value: control.value } } : null;
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
