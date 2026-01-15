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

import { Component, effect, linkedSignal } from "@angular/core";
import {
  MatExpansionPanel,
  MatExpansionPanelDescription,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatSlideToggle } from "@angular/material/slide-toggle";
import { MatIcon } from "@angular/material/icon";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatTooltip } from "@angular/material/tooltip";
import { EventsTabComponent } from "./tabs/events-tab/events-tab.component";
import { EventActionTabComponent } from "./tabs/event-action-tab/event-action-tab.component";
import { EventConditionsTabComponent } from "./tabs/event-conditions-tab/event-conditions-tab.component";
import { MatInput, MatLabel } from "@angular/material/input";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatFormField, MatHint } from "@angular/material/form-field";
import { MatOption, MatSelect } from "@angular/material/select";
import { EventPanelComponent } from "./event-panel.component";

@Component({
  selector: "app-event-panel-new",
  imports: [
    MatExpansionPanel,
    MatExpansionPanelDescription,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatIcon,
    MatIconButton,
    MatSlideToggle,
    MatTooltip,
    MatButton,
    EventsTabComponent,
    EventActionTabComponent,
    EventConditionsTabComponent,
    MatFormField,
    MatHint,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    FormsModule,
    MatSelect,
    MatOption
  ],
  templateUrl: "./event-panel-new.component.html",
  styleUrl: "./event-panel.component.scss"
})
export class EventPanelNewComponent extends EventPanelComponent {

  override isEditMode = linkedSignal(() => this.isExpanded());

  protected override readonly setHandlerModuleEffect = effect(() => {
    const modules = this.eventService.eventHandlerModules();
    if (this.isExpanded() && modules.length > 0 && !this.eventService.selectedHandlerModule()) {
      this.eventService.selectedHandlerModule.set(modules[0]);
    }
  });

}
