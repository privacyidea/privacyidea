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
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { LockoutPolicyStage, LockoutStageAction } from "@services/conditional-access/conditional-access-policy.service";
import { ConditionalAccessActionsListComponent } from "./actions-list/conditional-access-actions-list.component";

@Component({
  selector: "app-conditional-access-stage-item",
  standalone: true,
  imports: [MatButtonModule, MatFormFieldModule, MatIconModule, MatInputModule, ConditionalAccessActionsListComponent],
  templateUrl: "./conditional-access-stage-item.component.html",
  styleUrl: "./conditional-access-stage-item.component.scss"
})
export class ConditionalAccessStageItemComponent {
  readonly stage = input.required<LockoutPolicyStage>();
  readonly stageNumber = input.required<number>();
  readonly updateStage = output<Partial<LockoutPolicyStage>>();
  readonly removeStage = output<void>();

  onFailureThresholdInput(value: string): void {
    const parsed = parseInt(value, 10);
    if (!isNaN(parsed) && parsed >= 1) {
      this.updateStage.emit({ failure_threshold: parsed });
    }
  }

  onActionsChange(actions: LockoutStageAction[]): void {
    this.updateStage.emit({ actions });
  }

  onRemoveStage(): void {
    this.removeStage.emit();
  }
}
