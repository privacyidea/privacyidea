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
import { Component } from "@angular/core";
import { MatIconButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatCell, MatColumnDef, MatTableModule } from "@angular/material/table";
import { MatTooltip } from "@angular/material/tooltip";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { DetailsCardComponent } from "@components/shared/details-shared/details-card/details-card.component";
import { TokenDetailsUserComponent } from "./token-details-user.component";

@Component({
  selector: "app-token-details-user-self-service",
  standalone: true,
  imports: [
    MatTableModule,
    MatColumnDef,
    MatCell,
    MatIconButton,
    MatIcon,
    MatTooltip,
    CopyableComponent,
    DetailsCardComponent
  ],
  templateUrl: "./token-details-user.self-service.component.html",
  styleUrl: "./token-details-user.component.scss"
})
export class TokenDetailsUserSelfServiceComponent extends TokenDetailsUserComponent {}
