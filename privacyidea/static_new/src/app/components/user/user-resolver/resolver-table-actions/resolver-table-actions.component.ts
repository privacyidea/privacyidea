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
import { Component, inject } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatDialog, MatDialogModule } from "@angular/material/dialog";
import { AuthService } from "../../../../services/auth/auth.service";
import { UserNewResolverComponent } from "../../user-new-resolver/user-new-resolver.component";
import { Resolver } from "../../../../services/resolver/resolver.service";

@Component({
  selector: "app-resolver-table-actions",
  standalone: true,
  imports: [
    MatButtonModule,
    MatIconModule,
    MatDialogModule
  ],
  templateUrl: "./resolver-table-actions.component.html",
  styleUrl: "./resolver-table-actions.component.scss"
})
export class ResolverTableActionsComponent {
  protected readonly authService = inject(AuthService);
  private readonly dialog = inject(MatDialog);

  onNewResolver(): void {
    this.openResolverDialog();
  }

  private openResolverDialog(resolver?: Resolver): void {
    this.dialog.open(UserNewResolverComponent, {
      data: { resolver },
      width: "auto",
      height: "auto",
      maxWidth: "100vw",
      maxHeight: "100vh"
    });
  }
}
