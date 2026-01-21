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

import { Component, inject, input, linkedSignal } from "@angular/core";
import { ActionOptions, EventService } from "../../../../../services/event/event.service";
import { of } from "rxjs";

@Component({
  selector: "app-event-action-tab-read",
  imports: [],
  templateUrl: "./event-action-tab-read.component.html",
  styleUrl: "./event-action-tab-read.component.scss"
})
export class EventActionTabReadComponent {
  eventService = inject(EventService);
  action = input.required<string>();
  options = input.required<ActionOptions>();

  relevantOptions = linkedSignal(() => {
    let relevantOptions: Record<string, any> = {};
    const relevantOptionKeys = this.eventService.moduleActions()[this.action()];
    if (!relevantOptionKeys) {
      return {};
    }
    Object.entries(this.options()).forEach(([key, value]) => {
      if (key in relevantOptionKeys) {
        relevantOptions[key] = value;
      }
    });
    return relevantOptions;
  });

  protected readonly Object = Object;
  protected readonly of = of;
}
