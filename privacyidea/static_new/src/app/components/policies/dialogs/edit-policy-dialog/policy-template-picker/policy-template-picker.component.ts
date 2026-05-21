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
import { MatExpansionModule } from "@angular/material/expansion";
import { PolicyDetail } from "@services/policies/policies.service";
import {
  PolicyTemplate,
  PolicyTemplatesService,
  PolicyTemplatesServiceInterface
} from "@services/policy-templates/policy-templates.service";

@Component({
  selector: "app-policy-template-picker",
  standalone: true,
  imports: [MatExpansionModule],
  templateUrl: "./policy-template-picker.component.html",
  styleUrl: "./policy-template-picker.component.scss"
})
export class PolicyTemplatePickerComponent {
  readonly policyTemplatesService: PolicyTemplatesServiceInterface = inject(PolicyTemplatesService);

  readonly currentPriority = input<number>(1);
  readonly templateApplied = output<Partial<PolicyDetail>>();

  readonly isExpanded = signal(false);
  readonly templates = computed(() => {
    const index = this.policyTemplatesService.policyTemplatesIndex();
    return Object.entries(index).map(([name, description]) => ({ name, description }));
  });

  selectTemplate(templateName: string): void {
    this.policyTemplatesService.getTemplate(templateName).subscribe((template) => {
      if (!template) return;
      this.templateApplied.emit(this.buildPolicyEdits(template));
      this.isExpanded.set(false);
    });
  }

  private buildPolicyEdits(template: PolicyTemplate): Partial<PolicyDetail> {
    const edits: Partial<PolicyDetail> = {
      name: template.name,
      scope: template.scope,
      priority: this.currentPriority() || 1
    };
    if (template.realm !== undefined) edits.realm = template.realm;
    if (template.action !== undefined) edits.action = template.action;
    if (template.resolver !== undefined) edits.resolver = template.resolver;
    if (template.adminrealm !== undefined) edits.adminrealm = template.adminrealm;
    if (template.conditions !== undefined) edits.conditions = template.conditions;
    if (template.user_agents !== undefined) edits.user_agents = template.user_agents;
    return edits;
  }
}
