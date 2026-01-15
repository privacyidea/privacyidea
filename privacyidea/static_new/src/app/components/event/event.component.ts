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

import { Component, inject } from "@angular/core";
import { MatAccordion } from "@angular/material/expansion";
import { MatDivider } from "@angular/material/divider";
import { ScrollToTopDirective } from "../shared/directives/app-scroll-to-top.directive";
import { AuthService } from "../../services/auth/auth.service";
import { EMPTY_EVENT, EventService } from "../../services/event/event.service";
import { EventPanelComponent } from "./event-panel/event-panel.component";
import { EventPanelNewComponent } from "./event-panel/event-panel-new.component";

@Component({
  selector: "app-event",
  imports: [
    MatAccordion,
    MatDivider,
    ScrollToTopDirective,
    EventPanelComponent,
    EventPanelNewComponent
  ],
  standalone: true,
  templateUrl: "./event.component.html",
  styleUrl: "./event.component.scss"
})
export class EventComponent {
  protected readonly authService = inject(AuthService);
  protected readonly eventService = inject(EventService);
  protected readonly EMPTY_EVENT = EMPTY_EVENT;
}
