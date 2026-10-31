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

import { Component, computed, inject, input, output, signal } from "@angular/core";

import { form, FormField, validate } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MultiSelectOnlyComponent } from "@components/shared/multi-select-only/multi-select-only.component";
import { checkAllResolversWithoutResolver, PolicyDetail } from "@services/policies/policies.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { ResolverService, ResolverServiceInterface } from "@services/resolver/resolver.service";

@Component({
  selector: "app-edit-user-conditions",
  standalone: true,
  imports: [FormField, MatIconModule, MatInputModule, MatButtonModule, MultiSelectOnlyComponent, MatCheckboxModule],
  templateUrl: "./edit-user-conditions.component.html",
  styleUrl: "./edit-user-conditions.component.scss"
})
export class EditUserConditionsComponent {
  readonly realmService: RealmServiceInterface = inject(RealmService);
  readonly resolverService: ResolverServiceInterface = inject(ResolverService);

  readonly policy = input.required<PolicyDetail>();
  readonly policyEdit = output<Partial<PolicyDetail>>();

  readonly userSignal = signal("");
  readonly userField = form(this.userSignal, (f) => {
    validate(f, (ctx) => (/[,]/.test(ctx.value()) ? [{ kind: "includesComma" }] : []));
  });

  readonly selectedRealms = computed(() => this.policy().realm || []);
  readonly selectedResolvers = computed(() => this.policy().resolver || []);
  readonly selectedUsers = computed(() => this.policy().user || []);
  readonly userCaseInsensitive = computed(() => this.policy().user_case_insensitive || false);
  readonly checkAllResolvers = computed(() => this.policy().check_all_resolvers || false);
  readonly checkAllResolversWithoutResolver = computed(() => checkAllResolversWithoutResolver(this.policy()));

  readonly availableRealms = computed(() => {
    const selectedResolvers = this.selectedResolvers();
    if (selectedResolvers.length === 0) {
      return this.realmService.realmOptions();
    }
    const realms = this.realmService.realms();
    return Object.entries(realms)
      .filter(([, realm]) => realm.resolver.some((r) => selectedResolvers.includes(r.name)))
      .map(([name]) => name);
  });

  readonly availableResolvers = computed(() => {
    const realms = this.realmService.realms();
    const selectedRealms = this.selectedRealms();
    const realmNames = selectedRealms.length > 0 ? selectedRealms : Object.keys(realms);
    const resolversSet = new Set<string>();
    realmNames.forEach((realmName) => {
      realms[realmName]?.resolver.forEach((r) => resolversSet.add(r.name));
    });
    if (selectedRealms.length === 0) {
      // Without a selected realm, offer every resolver. Without the right to list the resolvers, the list is empty
      // and only the resolvers in a realm are known.
      this.resolverService.resolverOptions().forEach((name) => resolversSet.add(name));
    }
    return Array.from(resolversSet);
  });

  readonly selectResolverHint = computed(() => {
    if (this.selectedRealms().length > 0) {
      return $localize`:@@policy.resolversOfSelectedRealms:Lists the resolvers of the selected realms.`;
    }
    return this.resolverService.resolverOptions().length > 0
      ? $localize`:@@policy.allResolvers:Lists all resolvers.`
      : $localize`:@@policy.resolversOfAllRealms:Lists the resolvers of all realms. A resolver that is in no realm is not listed.`;
  });

  readonly selectResolverTooltip = computed(() =>
    this.availableResolvers().length === 0
      ? $localize`:@@policy.noResolversAvailable:No resolvers available for the selected realms.`
      : ""
  );

  readonly selectRealmTooltip = computed(() =>
    this.availableRealms().length === 0
      ? $localize`:@@policy.noRealmsAvailable:No realms available for the selected resolvers.`
      : ""
  );

  emitEdits(edits: Partial<PolicyDetail>) {
    this.policyEdit.emit(edits);
  }

  selectRealm(realmNames: string[]): void {
    this.emitEdits({ realm: realmNames });
  }

  selectResolver(resolverNames: string[]): void {
    this.emitEdits({ resolver: resolverNames });
  }

  toggleCheckAllResolvers() {
    this.emitEdits({ check_all_resolvers: !this.checkAllResolvers() });
  }

  addUser(user: string) {
    const trimmed = user?.trim();
    if (this.userField().errors().length > 0 || !trimmed) return;
    if (!this.selectedUsers().includes(trimmed)) {
      this.emitEdits({ user: [...this.selectedUsers(), trimmed] });
      this.userSignal.set("");
    }
  }

  removeUser(user: string) {
    this.emitEdits({ user: this.selectedUsers().filter((u) => u !== user) });
  }

  clearUsers() {
    this.emitEdits({ user: [] });
  }

  toggleUserCaseInsensitive() {
    this.emitEdits({ user_case_insensitive: !this.userCaseInsensitive() });
  }
}
