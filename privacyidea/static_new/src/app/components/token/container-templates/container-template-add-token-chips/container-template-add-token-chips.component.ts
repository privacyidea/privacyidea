/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { Component, EventEmitter, inject, Input, Output, ViewEncapsulation } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatCardModule } from "@angular/material/card";
import { MatChipListbox, MatChipsModule } from "@angular/material/chips";
import {
  ContainerTemplateService,
  ContainerTemplateServiceInterface
} from "../../../../services/container-template/container-template.service";
import { MatIcon } from "@angular/material/icon";

@Component({
  selector: "app-container-template-add-token-chips",
  standalone: true,
  imports: [CommonModule, MatCardModule, MatChipsModule, MatChipListbox, MatIcon],
  templateUrl: "./container-template-add-token-chips.component.html",
  styleUrls: ["./container-template-add-token-chips.component.scss"]
})
export class ContainerTemplateAddTokenChipsComponent {
  @Input({ required: true }) containerType: string = "";
  @Output() onAddToken = new EventEmitter<string>();

  containerTemplateService: ContainerTemplateServiceInterface = inject(ContainerTemplateService);

  get tokenTypes(): string[] {
    return this.containerTemplateService.getTokenTypesForContainerType(this.containerType);
  }

  addToken(tokenType: string) {
    this.onAddToken.emit(tokenType);
  }
}
