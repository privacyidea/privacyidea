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

import { Component, computed, input, linkedSignal, output } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import {
  ALL_LOCKOUT_ACTIONS,
  LockoutActionType,
  LockoutStageAction
} from "@services/conditional-access/conditional-access-policy.service";

// action_value is an arbitrary JSON payload whose shape depends on action_type (e.g. a lock
// duration for LOCK_USER, an SMTP identifier + template for EMAIL_ADMIN). Rather than building a
// bespoke sub-form per action type, it is edited as raw JSON here -- this mirrors the flexibility
// the backend already grants (privacyidea/lib/conditional_access/lockout_policy.py stores it as-is).
@Component({
  selector: "app-conditional-access-action-item",
  standalone: true,
  imports: [MatButtonModule, MatFormFieldModule, MatIconModule, MatInputModule, MatSelectModule],
  templateUrl: "./conditional-access-action-item.component.html",
  styleUrl: "./conditional-access-action-item.component.scss"
})
export class ConditionalAccessActionItemComponent {
  readonly action = input.required<LockoutStageAction>();
  readonly updateAction = output<Partial<LockoutStageAction>>();
  readonly removeAction = output<void>();

  readonly allActionTypes = ALL_LOCKOUT_ACTIONS;

  readonly actionValueText = linkedSignal(() => ConditionalAccessActionItemComponent.formatValue(this.action().action_value));
  readonly jsonError = computed<string | null>(() => {
    const text = this.actionValueText().trim();
    if (!text) {
      return null;
    }
    try {
      JSON.parse(text);
      return null;
    } catch {
      return $localize`Invalid JSON.`;
    }
  });

  private static formatValue(value: unknown): string {
    if (value === null || value === undefined) {
      return "";
    }
    return JSON.stringify(value, null, 2);
  }

  onActionTypeChange(actionType: LockoutActionType): void {
    this.updateAction.emit({ action_type: actionType });
  }

  onActionValueInput(text: string): void {
    this.actionValueText.set(text);
    const trimmed = text.trim();
    if (!trimmed) {
      this.updateAction.emit({ action_value: null });
      return;
    }
    try {
      const parsed = JSON.parse(trimmed);
      this.updateAction.emit({ action_value: parsed });
    } catch {
      // Invalid JSON while typing: keep the last valid action_value, surface jsonError instead.
    }
  }

  onRemoveAction(): void {
    this.removeAction.emit();
  }
}
