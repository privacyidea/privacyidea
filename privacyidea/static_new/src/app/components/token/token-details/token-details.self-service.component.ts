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
import { NgClass } from "@angular/common";
import { Component } from "@angular/core";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatAutocomplete, MatAutocompleteTrigger } from "@angular/material/autocomplete";
import { MatIconButton } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatListItem } from "@angular/material/list";
import { MatSelectModule } from "@angular/material/select";
import { MatCell, MatColumnDef, MatRow, MatTable, MatTableModule } from "@angular/material/table";
import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { CopyButtonComponent } from "../../shared/copy-button/copy-button.component";
import { EditButtonsComponent } from "../../shared/edit-buttons/edit-buttons.component";
import { TokenDetailsActionsComponent } from "./token-details-actions/token-details-actions.component";
import { TokenDetailsInfoComponent } from "./token-details-info/token-details-info.component";
import { TokenDetailsUserSelfServiceComponent } from "./token-details-user/token-details-user.self-service.component";
import { TokenDetailsComponent } from "./token-details.component";

@Component({
  selector: "app-token-details-self-service",
  standalone: true,
  imports: [
    MatCell,
    MatTableModule,
    MatColumnDef,
    MatIcon,
    MatListItem,
    MatRow,
    MatTable,
    NgClass,
    FormsModule,
    MatInput,
    MatFormFieldModule,
    MatSelectModule,
    ReactiveFormsModule,
    MatIconButton,
    TokenDetailsUserSelfServiceComponent,
    MatAutocomplete,
    MatAutocompleteTrigger,
    TokenDetailsInfoComponent,
    TokenDetailsActionsComponent,
    EditButtonsComponent,
    CopyButtonComponent,
    ClearableInputComponent
  ],
  templateUrl: "./token-details.self-service.component.html",
  styleUrls: ["./token-details.component.scss"]
})
export class TokenDetailsSelfServiceComponent extends TokenDetailsComponent {
  toggleActive(active: boolean): void {
    this.tokenService.toggleActive(this.tokenSerial(), active).subscribe(() => {
      this.tokenService.tokenDetailResource.reload();
    });
  }
}
