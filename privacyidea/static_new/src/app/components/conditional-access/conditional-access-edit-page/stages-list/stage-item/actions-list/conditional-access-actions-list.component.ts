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

import { Component, input, output } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { LockoutStageAction } from "@services/conditional-access/conditional-access-policy.service";
import {
  ConditionalAccessActionItemComponent
} from "./action-item/conditional-access-action-item.component";

const NEW_ACTION: LockoutStageAction = { action_type: "LOCK_USER", action_value: null };

@Component({
  selector: "app-conditional-access-actions-list",
  standalone: true,
  imports: [MatButtonModule, MatIconModule, ConditionalAccessActionItemComponent],
  templateUrl: "./conditional-access-actions-list.component.html",
  styleUrl: "./conditional-access-actions-list.component.scss"
})
export class ConditionalAccessActionsListComponent {
  readonly actions = input.required<LockoutStageAction[]>();
  readonly actionsChange = output<LockoutStageAction[]>();

  onAddAction(): void {
    this.actionsChange.emit([...this.actions(), { ...NEW_ACTION }]);
  }

  onUpdateAction(index: number, partial: Partial<LockoutStageAction>): void {
    this.actionsChange.emit(
      this.actions().map((action, i) => (i === index ? { ...action, ...partial } : action))
    );
  }

  onRemoveAction(index: number): void {
    this.actionsChange.emit(this.actions().filter((_, i) => i !== index));
  }
}
