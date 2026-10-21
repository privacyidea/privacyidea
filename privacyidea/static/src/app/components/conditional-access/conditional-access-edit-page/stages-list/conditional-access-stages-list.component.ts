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

import { Component, input } from "@angular/core";
import { FieldTree } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { ConditionalAccessStageFormModel } from "@services/conditional-access/conditional-access-policy-form";
import { ConditionalAccessTarget } from "@services/conditional-access/conditional-access-policy.service";
import { ConditionalAccessStageItemComponent } from "./stage-item/conditional-access-stage-item.component";

const NEW_STAGE: ConditionalAccessStageFormModel = {
  id: null,
  name: "",
  has_error_message: false,
  error_message: "",
  failure_threshold: 1,
  actions: []
};

@Component({
  selector: "app-conditional-access-stages-list",
  standalone: true,
  imports: [MatButtonModule, MatIconModule, ConditionalAccessStageItemComponent],
  templateUrl: "./conditional-access-stages-list.component.html",
  styleUrl: "./conditional-access-stages-list.component.scss"
})
export class ConditionalAccessStagesListComponent {
  // The stage fields of the policy form; the list adds and removes stages through them and each item edits its own.
  readonly stages = input.required<FieldTree<ConditionalAccessStageFormModel[]>>();
  readonly target = input<ConditionalAccessTarget>("user");

  // 1-based order in which this stage triggers (lowest threshold = Stage 1), recomputed live so
  // editing a threshold re-numbers the stages. A stage without a threshold yet sorts last.
  stageNumber(stage: FieldTree<ConditionalAccessStageFormModel>): number {
    const threshold = stage.failure_threshold().value() ?? Infinity;
    return (
      this.stages()()
        .value()
        .filter((other) => (other.failure_threshold ?? Infinity) < threshold).length + 1
    );
  }

  onAddStage(): void {
    this.stages()().value.update((stages) => [...stages, { ...NEW_STAGE, actions: [] }]);
  }

  onRemoveStage(index: number): void {
    this.stages()().value.update((stages) => stages.filter((_, i) => i !== index));
  }
}
