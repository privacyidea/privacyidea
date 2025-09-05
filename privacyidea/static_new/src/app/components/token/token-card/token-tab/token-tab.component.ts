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
import { Component, inject, signal } from "@angular/core";
import { MatButton } from "@angular/material/button";
import { MatDialog } from "@angular/material/dialog";
import { MatDivider } from "@angular/material/divider";
import { MatIcon } from "@angular/material/icon";
import { MatList, MatListItem } from "@angular/material/list";
import { Router, RouterLink } from "@angular/router";
import { catchError, concatMap, EMPTY, filter, from, reduce, switchMap } from "rxjs";
import { tabToggleState } from "../../../../../styles/animations/animations";
import { AuditService, AuditServiceInterface } from "../../../../services/audit/audit.service";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { BulkResult, TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { VersioningService, VersioningServiceInterface } from "../../../../services/version/version.service";
import { ConfirmationDialogComponent } from "../../../shared/confirmation-dialog/confirmation-dialog.component";
import { SelectedUserAssignDialogComponent } from "../selected-user-attach-dialog/selected-user-attach-dialog.component";
import { tap } from "rxjs/operators";
import { LostTokenComponent } from "./lost-token/lost-token.component";
import { ROUTE_PATHS } from "../../../../route_paths";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../services/notification/notification.service";
import { PiResponse } from "../../../../app.component";
import { FilterValue } from "../../../../core/models/filter_value";

@Component({
  selector: "app-token-tab",
  standalone: true,
  imports: [MatIcon, MatList, MatListItem, MatButton, MatDivider, NgClass, RouterLink],
  templateUrl: "./token-tab.component.html",
  styleUrl: "./token-tab.component.scss",
  animations: [tabToggleState]
})
export class TokenTabComponent {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly dialog: MatDialog = inject(MatDialog);
  protected readonly auditService: AuditServiceInterface = inject(AuditService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  private router = inject(Router);
  tokenIsActive = this.tokenService.tokenIsActive;
  tokenIsRevoked = this.tokenService.tokenIsRevoked;
  tokenSerial = this.tokenService.tokenSerial;
  tokenSelection = this.tokenService.tokenSelection;
  isLost = signal(false);
  version!: string;

  ngOnInit(): void {
    this.version = this.versioningService.getVersion();
  }

  toggleActive(): void {
    this.tokenService.toggleActive(this.tokenSerial(), this.tokenIsActive()).subscribe({
      next: () => {
        this.tokenService.tokenDetailResource.reload();
      }
    });
  }

  revokeToken(): void {
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serialList: [this.tokenSerial()],
          title: "Revoke Token",
          type: "token",
          action: "revoke",
          numberOfTokens: 1
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.tokenService
              .revokeToken(this.tokenSerial())
              .pipe(switchMap(() => this.tokenService.getTokenDetails(this.tokenSerial())))
              .subscribe({
                next: () => {
                  this.tokenService.tokenDetailResource.reload();
                }
              });
          }
        }
      });
  }

  deleteToken(): void {
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serialList: [this.tokenSerial()],
          title: "Delete Token",
          type: "token",
          action: "delete",
          numberOfTokens: 1
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.tokenService.deleteToken(this.tokenSerial()).subscribe({
              next: () => {
                this.router.navigateByUrl(ROUTE_PATHS.TOKENS).then();
                this.tokenSerial.set("");
              }
            });
          }
        }
      });
  }

  deleteSelectedTokens(): void {
    const selectedTokens = this.tokenSelection();
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serialList: selectedTokens.map((token) => token.serial),
          title: "Delete Selected Tokens",
          type: "token",
          action: "delete",
          numberOfTokens: selectedTokens.length
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.tokenService.bulkDeleteTokens(selectedTokens).subscribe({
              next: (response: PiResponse<BulkResult, any>) => {
                const failedTokens = response.result?.value?.failed || [];
                const unauthorizedTokens = response.result?.value?.unauthorized || [];
                const count_success = response.result?.value?.count_success || 0;
                const messages: string[] = [];
                if (count_success) {
                  messages.push(`Successfully deleted ${count_success} token${count_success === 1 ? '' : 's'}.`);
                }

                if (failedTokens.length > 0) {
                  messages.push(`The following tokens failed to delete: ${failedTokens.join(", ")}`);
                }

                if (unauthorizedTokens.length > 0) {
                  messages.push(
                    `You are not authorized to delete the following tokens: ${unauthorizedTokens.join(", ")}`
                  );
                }

                if (messages.length > 0) {
                  this.notificationService.openSnackBar(messages.join("\n"));
                }

                this.tokenService.tokenResource.reload();
              },
              error: (err) => {
                let message = "An error occurred while deleting tokens.";
                if (err.error?.result?.error?.message) {
                  message = err.error.result.error.message;
                }
                this.notificationService.openSnackBar(message);
              }
            });
          }
        }
      });
  }

  openLostTokenDialog() {
    this.dialog.open(LostTokenComponent, {
      data: {
        isLost: this.isLost,
        tokenSerial: this.tokenSerial
      }
    });
  }

  assignSelectedTokens() {
    this.dialog
      .open(SelectedUserAssignDialogComponent)
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap((result) =>
          from(this.tokenSelection()).pipe(
            concatMap((token) => {
              const assign$ = this.tokenService.assignUser({
                tokenSerial: token.serial,
                username: result.username,
                realm: result.realm
              });
              return token.username
                ? this.tokenService.unassignUser(token.serial).pipe(switchMap(() => assign$))
                : assign$;
            }),
            reduce(() => null, null),
            switchMap(() => this.tokenService.getTokenDetails(this.tokenSerial()))
          )
        ),
        tap(() => this.tokenService.tokenResource.reload()),
        catchError((err) => {
          let message = "An error occurred while assigning tokens.";
          if (err.error?.result?.error?.message) {
            message = err.error.result.error.message;
          }
          this.notificationService.openSnackBar(message);
          return EMPTY;
        })
      )
      .subscribe();
  }

  onClickManageSearch(): void {
    this.auditService.auditFilter.set(new FilterValue({ value: `serial: ${this.tokenSerial()}` }));
  }

  unassignSelectedTokens() {
    const selectedTokens = this.tokenSelection();
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serialList: selectedTokens.map((token) => token.serial),
          title: "Unassign Selected Tokens",
          type: "token",
          action: "unassign",
          numberOfTokens: selectedTokens.length
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.tokenService.bulkUnassignTokens(selectedTokens).subscribe({
              next: (response: PiResponse<BulkResult, any>) => {
                const failedTokens = response.result?.value?.failed || [];
                const unauthorizedTokens = response.result?.value?.unauthorized || [];
                const count_success = response.result?.value?.count_success || 0;
                const messages: string[] = [];

                if (count_success) {
                  messages.push(`Successfully unassigned ${count_success} token${count_success === 1 ? '' : 's'}.`);
                }

                if (failedTokens.length > 0) {
                  messages.push(`The following tokens failed to unassign: ${failedTokens.join(", ")}`);
                }

                if (unauthorizedTokens.length > 0) {
                  messages.push(
                    `You are not authorized to unassign the following tokens: ${unauthorizedTokens.join(", ")}`
                  );
                }

                if (messages.length > 0) {
                  this.notificationService.openSnackBar(messages.join("\n"));
                }
                this.tokenService.tokenResource.reload();
              },
              error: (err) => {
                let message = "An error occurred while unassigning tokens.";
                if (err.error?.result?.error?.message) {
                  message = err.error.result.error.message;
                }
                this.notificationService.openSnackBar(message);
              }
            });
          }
        }
      });
  }
}
