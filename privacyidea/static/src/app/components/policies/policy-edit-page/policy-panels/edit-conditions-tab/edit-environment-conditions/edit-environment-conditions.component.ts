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

import {
  Component,
  computed,
  effect,
  inject,
  input,
  OnInit,
  output,
  signal,
  untracked,
  ViewChild
} from "@angular/core";

import { form, FormField, validate } from "@angular/forms/signals";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelect, MatSelectChange, MatSelectModule } from "@angular/material/select";
import { ChipListInputComponent } from "@components/shared/chip-list-input/chip-list-input.component";
import { ClearButtonComponent } from "@components/shared/clear-button/clear-button.component";
import { MultiSelectOnlyComponent } from "@components/shared/multi-select-only/multi-select-only.component";
import { ClientsService, ClientsServiceInterface } from "@services/clients/clients.service";
import { IntegrationsService, IntegrationsServiceInterface } from "@services/integrations/integrations.service";
import {
  PolicyDetail,
  PolicyService,
  PolicyServiceInterface,
  UserAgentOption
} from "@services/policies/policies.service";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";
import { hasError } from "@utils/form-state.utils";

interface ClientSuggestion {
  ip: string;
  hostname?: string;
  applications: string[];
}

interface TimeRange {
  days: string;
  startMinutes: number;
  endMinutes: number;
}

export interface OvernightTimeRange {
  days: string;
  start: string;
  end: string;
}

const WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

function toMinutes(time: string): number | null {
  const [hours, minutes = 0] = time.split(":").map(Number);
  return hours <= 23 && minutes <= 59 ? hours * 60 + minutes : null;
}

function formatMinutes(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  return `${String(hours).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
}

function formatDayName(day: string): string {
  return day.charAt(0).toUpperCase() + day.slice(1).toLowerCase();
}

// Mirrors check_time_in_range on the server: whitespace is ignored and day names are case-insensitive.
// A day range can wrap around the end of the week (Sat-Mon) and a time range can cross midnight (22-6).
// Returns null if one of the ranges is not valid.
function parseTimeRanges(value: string): TimeRange[] | null {
  const timeRanges: TimeRange[] = [];
  for (const range of value.replace(/\s+/g, "").split(",")) {
    const match = /^([a-z]{3})(?:-([a-z]{3}))?:(\d{1,2}(?::\d{1,2})?)-(\d{1,2}(?::\d{1,2})?)$/i.exec(range);
    if (!match) return null;
    const [, dayStart, dayEnd, timeStart, timeEnd] = match;
    const dayNames = dayEnd === undefined ? [dayStart] : [dayStart, dayEnd];
    if (!dayNames.every((day) => WEEKDAYS.includes(day.toLowerCase()))) return null;
    const startMinutes = toMinutes(timeStart);
    const endMinutes = toMinutes(timeEnd);
    if (startMinutes === null || endMinutes === null) return null;
    timeRanges.push({ days: dayNames.map(formatDayName).join("-"), startMinutes, endMinutes });
  }
  return timeRanges;
}

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
    MatAutocompleteModule,
    ChipListInputComponent
  ],
  templateUrl: "./edit-environment-conditions.component.html",
  styleUrl: "./edit-environment-conditions.component.scss"
})
export class EditEnvironmentConditionsComponent implements OnInit {
  @ViewChild("nodeSelect") nodeSelect!: MatSelect;

  readonly policyService: PolicyServiceInterface = inject(PolicyService);
  readonly systemService: SystemServiceInterface = inject(SystemService);
  readonly clientsService: ClientsServiceInterface = inject(ClientsService);
  readonly integrationsService: IntegrationsServiceInterface = inject(IntegrationsService);

  readonly policy = input.required<PolicyDetail>();
  readonly policyEdit = output<Partial<PolicyDetail>>();

  protected readonly hasError = hasError;

  readonly validTimeSignal = signal("");
  readonly validTimeField = form(this.validTimeSignal, (f) => {
    validate(f, (ctx) => {
      const value = ctx.value();
      if (!value) return [];
      return parseTimeRanges(value) !== null ? [] : [{ kind: "invalidValidTime" }];
    });
  });

  // A range that ends before it starts is valid and crosses midnight. The hint shows these ranges, so that an admin
  // sees that a swapped range like "Mon-Fri: 18-8" applies at night and not from 08:00 to 18:00.
  readonly overnightTimeRanges = computed<OvernightTimeRange[]>(() =>
    (parseTimeRanges(this.validTimeSignal()) ?? [])
      .filter((timeRange) => timeRange.startMinutes > timeRange.endMinutes)
      .map((timeRange) => ({
        days: timeRange.days,
        start: formatMinutes(timeRange.startMinutes),
        end: formatMinutes(timeRange.endMinutes)
      }))
  );

  readonly regexIpV4 =
    /^!?(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:\/(?:[0-9]|[12]\d|3[0-2]))?$/;
  readonly regexIpV6 =
    /^!?(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))(?:\/(?:[0-9]|[1-9]\d|1[01]\d|12[0-8]))?$/;
  readonly regexHostname =
    /^!?(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9])\.)+([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9-]*[A-Za-z0-9])$/;

  readonly clientSignal = signal("");
  readonly clientField = form(this.clientSignal, (f) => {
    validate(f, (ctx) => {
      const value = ctx.value();
      if (!value) return [];
      const invalidClients = value
        .split(",")
        .map((c: string) => c.trim())
        .filter((c: string) => c !== "")
        .filter((c: string) => !this.regexIpV4.test(c) && !this.regexIpV6.test(c) && !this.regexHostname.test(c));
      return invalidClients.length > 0 ? [{ kind: "invalidClient" }] : [];
    });
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
    const segment = this.currentClientSegment(this.clientSignal()).raw;
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

  readonly userAgentOptions = computed<UserAgentOption[]>(() =>
    this.integrationsService.integrations().map((integration) => ({
      key: integration.policy_value,
      label: integration.label
    }))
  );
  getUserAgentDisplay = (userAgent: string): string => this.integrationsService.displayForPolicyValue(userAgent);

  readonly availablePinodesList = computed(() => this.systemService.nodes().map((node) => node.name));
  readonly selectedPinodes = computed<string[]>(() => this.policy().pinode || []);
  readonly selectedUserAgents = computed(() => this.policy().user_agents || []);

  readonly availableUserAgentPresets = computed(() => {
    const selected = this.selectedUserAgents();
    return this.userAgentOptions().filter((ua) => !selected.includes(ua.key));
  });

  private clientInitialized = false;

  constructor() {
    effect(() => {
      const value = this.validTimeSignal();
      if (this.validTimeField().errors().length === 0) {
        this.emitEdits({ time: value || "" });
      }
    });
    effect(() => {
      this.clientSignal();
      if (!this.clientInitialized) {
        this.clientInitialized = true;
        return;
      }
      untracked(() => this.setClients());
    });
  }

  ngOnInit() {
    this.validTimeSignal.set(this.policy().time || "");
    this.clientSignal.set(this.policy().client?.join(", ") || "");
    this.clientsService.requestClientsForAutocomplete();
  }

  private currentClientSegment(value: string): { before: string; raw: string } {
    const idx = value.lastIndexOf(",");
    if (idx === -1) return { before: "", raw: value };
    return { before: value.slice(0, idx + 1), raw: value.slice(idx + 1) };
  }

  buildClientSelection(ip: string): string {
    const value = this.clientSignal();
    const { before, raw } = this.currentClientSegment(value);
    const negation = /^\s*!/.test(raw) ? "!" : "";
    const separator = before ? " " : "";
    return `${before}${separator}${negation}${ip}, `;
  }

  emitEdits(edits: Partial<PolicyDetail>) {
    this.policyEdit.emit(edits);
  }

  updateSelectedPinodes($event: string[]) {
    this.emitEdits({ pinode: $event });
  }

  addUserAgentFromSelect($event: MatSelectChange, selectRef: MatSelect) {
    this.addUserAgentValue($event.value);
    setTimeout(() => (selectRef.value = null));
  }

  private addUserAgentValue(userAgent: string | null | undefined) {
    if (!userAgent) return;
    const oldUserAgents = this.selectedUserAgents();
    if (!oldUserAgents.includes(userAgent)) {
      this.emitEdits({ user_agents: [...oldUserAgents, userAgent] });
    }
  }

  clearUserAgents() {
    this.emitEdits({ user_agents: [] });
  }

  clearValidTimeControl() {
    this.validTimeSignal.set("");
  }

  setClients() {
    const client = this.clientSignal();
    if (this.clientField().valid()) {
      const clientsArray = client
        ? client
            .split(",")
            .map((c: string) => c.trim())
            .filter((c: string) => c !== "")
        : [];
      this.emitEdits({ client: clientsArray });
    }
  }

  clearClientControl() {
    this.clientSignal.set("");
  }
}
