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
import { Injectable, signal, Signal } from "@angular/core";
import { AdditionalCondition } from "@services/policies/policies.service";
import { POLICY_TEMPLATE_INDEX, POLICY_TEMPLATES } from "./policy-templates.constants";

export type PolicyTemplateIndex = Record<string, string>;

export interface PolicyTemplate {
  name: string;
  scope: string;
  description?: string;
  action?: Record<string, string | boolean>;
  realm?: string[];
  resolver?: string[];
  adminrealm?: string[];
  conditions?: AdditionalCondition[];
  user_agents?: string[];
}

export interface PolicyTemplatesServiceInterface {
  readonly policyTemplatesIndex: Signal<PolicyTemplateIndex>;

  getTemplate(templateName: string): PolicyTemplate | undefined;
}

@Injectable({
  providedIn: "root"
})
export class PolicyTemplatesService implements PolicyTemplatesServiceInterface {
  readonly policyTemplatesIndex: Signal<PolicyTemplateIndex> = signal(POLICY_TEMPLATE_INDEX).asReadonly();

  getTemplate(templateName: string): PolicyTemplate | undefined {
    return POLICY_TEMPLATES[templateName];
  }
}
