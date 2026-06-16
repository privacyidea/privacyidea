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
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { DetailFieldComponent } from "@components/shared/details-shared/detail-field/detail-field.component";
import { DetailsEditRegistry } from "@components/shared/details-shared/details-edit-registry.service";
import { DetailsCardComponent } from "@components/shared/details-shared/details-card/details-card.component";
import { DetailsHeaderComponent } from "@components/shared/details-shared/details-header/details-header.component";
import { EditButtonsComponent } from "@components/shared/edit-buttons/edit-buttons.component";
import { TokenDetailsMachineComponent } from "@components/token/token-details/token-details-machine/token-details-machine.component";
import { TokenDetailsActionsComponent } from "./token-details-actions/token-details-actions.component";
import { TokenContainerFieldComponent } from "./fields/token-container-field.component";
import { TokenFailcountFieldComponent } from "./fields/token-failcount-field.component";
import { TokenRealmsFieldComponent } from "./fields/token-realms-field.component";
import { TokenTokengroupFieldComponent } from "./fields/token-tokengroup-field.component";
import { TokenDetailsInfoComponent } from "./token-details-info/token-details-info.component";
import { TokenDetailsUserSelfServiceComponent } from "./token-details-user/token-details-user.self-service.component";
import { TokenDetailsComponent } from "./token-details.component";

@Component({
  selector: "app-token-details-self-service",
  standalone: true,
  imports: [
    DetailsCardComponent,
    MatInput,
    MatFormFieldModule,
    TokenDetailsUserSelfServiceComponent,
    TokenDetailsInfoComponent,
    TokenDetailsActionsComponent,
    DetailFieldComponent,
    TokenFailcountFieldComponent,
    TokenRealmsFieldComponent,
    TokenTokengroupFieldComponent,
    TokenContainerFieldComponent,
    EditButtonsComponent,
    TokenDetailsMachineComponent,
    DetailsHeaderComponent
  ],
  providers: [DetailsEditRegistry],
  templateUrl: "./token-details.self-service.component.html",
  styleUrls: ["./token-details.component.scss"]
})
export class TokenDetailsSelfServiceComponent extends TokenDetailsComponent {}
