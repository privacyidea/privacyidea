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
import { DetailsEditRegistry } from "@components/shared/details-shared/field-editing/details-edit-registry.service";
import { DetailsHeaderComponent } from "@components/shared/details-shared/details-header/details-header.component";
import { TokenDetailsMachineComponent } from "@components/token/token-details/token-details-machine/token-details-machine.component";
import { TokenDetailsActionsComponent } from "./token-details-actions/token-details-actions.component";
import { TokenDetailsAssignmentsComponent } from "./token-details-assignments/token-details-assignments.component";
import { TokenDetailsCountersComponent } from "./token-details-counters/token-details-counters.component";
import { TokenDetailsDescriptionComponent } from "./token-details-description/token-details-description.component";
import { TokenDetailsInfoComponent } from "./token-details-info/token-details-info.component";
import { TokenDetailsStatusComponent } from "./token-details-status/token-details-status.component";
import { TokenDetailsUserSelfServiceComponent } from "./token-details-user/token-details-user.self-service.component";
import { TokenDetailsComponent } from "./token-details.component";

@Component({
  selector: "app-token-details-self-service",
  standalone: true,
  imports: [
    TokenDetailsUserSelfServiceComponent,
    TokenDetailsInfoComponent,
    TokenDetailsActionsComponent,
    TokenDetailsStatusComponent,
    TokenDetailsCountersComponent,
    TokenDetailsAssignmentsComponent,
    TokenDetailsDescriptionComponent,
    TokenDetailsMachineComponent,
    DetailsHeaderComponent
  ],
  providers: [DetailsEditRegistry],
  templateUrl: "./token-details.self-service.component.html",
  styleUrls: ["./token-details.component.scss"]
})
export class TokenDetailsSelfServiceComponent extends TokenDetailsComponent {}
