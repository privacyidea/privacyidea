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
import { Component, computed, inject, Input, WritableSignal } from "@angular/core";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import {
  ContainerDetailToken,
  ContainerService,
  ContainerServiceInterface
} from "../../../../services/container/container.service";
import { MatIcon } from "@angular/material/icon";
import { MatButton } from "@angular/material/button";
import { MatDivider } from "@angular/material/divider";
import { SimpleConfirmationDialogComponent } from "../../../shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { MatTableDataSource } from "@angular/material/table";
import { DialogService, DialogServiceInterface } from "../../../../services/dialog/dialog.service";

@Component({
  selector: "app-container-details-token-actions",
  templateUrl: "./container-details-token-actions.component.html",
  imports: [MatIcon, MatButton, MatDivider],
  styleUrl: "./container-details-token-actions.component.scss"
})
export class ContainerDetailsTokenActionsComponent {
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);

  @Input() containerSerial!: string;
  @Input() user!: WritableSignal<{
    user_realm: string;
    user_name: string;
    user_resolver: string;
    user_id: string;
  }>;
  @Input() tokenData!: WritableSignal<MatTableDataSource<ContainerDetailToken>>;

  isAssignableToAllToken = computed<boolean>(() => {
    const assignedUser = this.user();
    if (assignedUser.user_name === "") {
      return false;
    }
    const tokens = this.tokenData().data;
    return tokens.some((token) => token.username === "" || !token.username);
  });

  isUnassignableFromAllToken = computed<boolean>(() => {
    const tokens = this.tokenData().data;
    return tokens.some((token) => token.username && token.username !== "");
  });

  anyActiveTokens = computed(() => {
    return this.tokenData().data.some((token) => token.active);
  });

  anyDisabledTokens = computed(() => {
    // explicitly check to be false to exclude undefined states
    return this.tokenData().data.some((token) => token.active === false);
  });

  unassignFromAllToken() {
    const tokenToUnassign = this.tokenData().data.filter((token) => token.username !== "");
    if (tokenToUnassign.length === 0) {
      return;
    }
    const tokenSerials = tokenToUnassign.map((token) => token.serial);
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          type: "token",
          serialList: tokenSerials,
          title: "Unassign User from All Tokens",
          action: "unassign",
          numberOfTokens: tokenSerials.length
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.tokenService.unassignUserFromAll(tokenSerials).subscribe({
              next: () => {
                this.containerService.containerDetailResource.reload();
              },
              error: (error) => {
                console.error("Error unassigning user from token:", error);
              }
            });
          }
        }
      });
  }

  assignToAllToken() {
    const username = this.user().user_name;
    const realm = this.user().user_realm;
    const tokensToAssign = this.tokenData().data.filter((token) => {
      return token.username !== username;
    });
    if (tokensToAssign.length === 0) {
      return;
    }
    const tokensAssignedToOtherUser = tokensToAssign.filter((token) => token.username !== "");
    const tokenSerialsAssignedToOtherUser = tokensAssignedToOtherUser.map((token) => token.serial);
    this.tokenService.unassignUserFromAll(tokenSerialsAssignedToOtherUser).subscribe({
      next: () => {
        const tokenSerialsToAssign = tokensToAssign.map((token) => token.serial);
        this.tokenService
          .assignUserToAll({
            tokenSerials: tokenSerialsToAssign,
            username: username,
            realm: realm
          })
          .subscribe({
            next: () => this.containerService.containerDetailResource.reload(),
            error: (error) => console.error("Error assigning user to all tokens:", error)
          });
      }
    });
  }

  toggleAll(action: "activate" | "deactivate") {
    this.containerService.toggleAll(action).subscribe({
      next: () => {
        this.containerService.containerDetailResource.reload();
      }
    });
  }

  removeAll() {
    const serialList = this.tokenData()
      .data.map((token) => token.serial)
      .join(",");
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          serialList: serialList.split(","),
          title: "Remove Token",
          type: "token",
          action: "remove",
          numberOfTokens: serialList.split(",").length
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.containerService.removeAll(this.containerSerial).subscribe({
              next: () => {
                this.containerService.containerDetailResource.reload();
              }
            });
          }
        }
      });
  }

  deleteAllTokens() {
    const serialList = this.tokenData().data.map((token) => token.serial);
    this.tokenService.bulkDeleteWithConfirmDialog(serialList, this.dialog, () =>
      this.containerService.containerDetailResource.reload()
    );
  }
}
