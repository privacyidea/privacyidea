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
import { Component, EventEmitter, Input, Output } from "@angular/core";
import { CopyButtonComponent } from "../../copy-button/copy-button.component";
import { MatIcon } from "@angular/material/icon";
import { MatIconButton } from "@angular/material/button";
import { MatTooltip } from "@angular/material/tooltip";
import { RouterLink } from "@angular/router";

@Component({
  selector: "app-details-header",
  standalone: true,
  imports: [CopyButtonComponent, MatIcon, MatIconButton, MatTooltip, RouterLink],
  templateUrl: "./details-header.component.html"
})
export class DetailsHeaderComponent {
  @Input({ required: true }) serial!: string;
  @Input() entityLabel = "Token";
  @Input() showAuditButton = false;
  @Input() auditRoute = "/audit";
  @Input() auditTooltip = "Show in audit log";

  @Output() auditClick = new EventEmitter<void>();
}

