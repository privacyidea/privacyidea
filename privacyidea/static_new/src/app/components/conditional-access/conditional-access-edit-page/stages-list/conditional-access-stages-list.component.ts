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
import { LockoutPolicyStage } from "@services/conditional-access/conditional-access-policy.service";
import { ConditionalAccessStageItemComponent } from "./stage-item/conditional-access-stage-item.component";

const NEW_STAGE: LockoutPolicyStage = { failure_threshold: 1, priority: 1, actions: [] };

@Component({
  selector: "app-conditional-access-stages-list",
  standalone: true,
  imports: [MatButtonModule, MatIconModule, ConditionalAccessStageItemComponent],
  templateUrl: "./conditional-access-stages-list.component.html",
  styleUrl: "./conditional-access-stages-list.component.scss"
})
export class ConditionalAccessStagesListComponent {
  readonly stages = input.required<LockoutPolicyStage[]>();
  readonly stagesChange = output<LockoutPolicyStage[]>();

  onAddStage(): void {
    this.stagesChange.emit([...this.stages(), { ...NEW_STAGE, actions: [] }]);
  }

  onUpdateStage(index: number, partial: Partial<LockoutPolicyStage>): void {
    this.stagesChange.emit(this.stages().map((stage, i) => (i === index ? { ...stage, ...partial } : stage)));
  }

  onRemoveStage(index: number): void {
    this.stagesChange.emit(this.stages().filter((_, i) => i !== index));
  }
}
