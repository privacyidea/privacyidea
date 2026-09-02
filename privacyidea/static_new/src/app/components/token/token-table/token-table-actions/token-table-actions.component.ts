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
import { Component, DOCUMENT, inject, LOCALE_ID } from "@angular/core";

import { MatButtonModule } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatTooltipModule } from "@angular/material/tooltip";
import { PiResponse } from "@app/app.component";
import { ROUTE_PATHS } from "@app/route_paths";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { AuditService, AuditServiceInterface } from "@services/audit/audit.service";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { BulkResult, TokenService, TokenServiceInterface } from "@services/token/token.service";
import { VersioningService, VersioningServiceInterface } from "@services/version/version.service";
import { catchError, concatMap, EMPTY, filter, from, reduce, switchMap } from "rxjs";
import { tap } from "rxjs/operators";
import { SelectedUserAssignDialogComponent } from "./selected-user-attach-dialog/selected-user-attach-dialog.component";
import { ToggleActiveAction, ToggleActiveDialogComponent } from "./toggle-active-dialog/toggle-active-dialog.component";

import { MatMenuModule } from "@angular/material/menu";
import { Router, RouterLink } from "@angular/router";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { DocumentationService, DocumentationServiceInterface } from "@services/documentation/documentation.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { formatList, pluralize } from "@utils/i18n.utils";
import { OverflowNavDirective } from "../../../shared/directives/overflow-nav/overflow-nav.directive";

@Component({
  selector: "app-token-table-actions",
  imports: [MatButtonModule, MatIcon, MatMenuModule, MatTooltipModule, OverflowNavDirective, RouterLink],
  templateUrl: "./token-table-actions.component.html",
  styleUrl: "./token-table-actions.component.scss"
})
export class TokenTableActionsComponent {
  private readonly localeId: string = inject(LOCALE_ID);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  private readonly document: Document = inject(DOCUMENT);
  protected readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  protected readonly documentationService: DocumentationServiceInterface = inject(DocumentationService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly auditService: AuditServiceInterface = inject(AuditService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  readonly ROUTE_PATHS = ROUTE_PATHS;
  readonly advancedApiFilterKeys = this.tokenService.advancedApiFilterKeys;
  private router = inject(Router);
  tokenIsActive = this.tokenService.tokenIsActive;
  tokenIsRevoked = this.tokenService.tokenIsRevoked;
  tokenSerial = this.tokenService.tokenSerial;
  tokenSelection = this.tokenService.tokenSelection;

  toggleActive(): void {
    this.tokenService.toggleActive(this.tokenSerial(), this.tokenIsActive()).subscribe({
      next: () => {
        this.tokenService.tokenDetailResource.reload();
      }
    });
  }

  revokeToken(): void {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`:@@token.revokeToken:Revoke Token`,
          items: [this.tokenSerial()],
          itemType: $localize`:@@common.itemTypeToken:token`,
          confirmAction: { label: $localize`:@@token.revoke:Revoke`, value: true, type: "destruct" }
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
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`:@@common.deleteToken:Delete Token`,
          items: [this.tokenSerial()],
          itemType: $localize`:@@common.itemTypeToken:token`,
          confirmAction: { label: $localize`:@@common.delete:Delete`, value: true, type: "destruct" }
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
    const serialList = this.tokenSelection.selectedRows().map((token) => token.serial);
    this.tokenService.bulkDeleteWithConfirmDialog(serialList, () => this.tokenService.tokenResource.reload());
  }

  toggleActiveSelectedTokens(): void {
    const selectedTokens = this.tokenSelection.selectedRows();
    if (selectedTokens.length === 0) return;
    this.dialogService
      .openDialog({
        component: ToggleActiveDialogComponent,
        data: {
          items: selectedTokens.map((token) => ({ serial: token.serial, active: token.active }))
        }
      })
      .afterClosed()
      .subscribe({
        next: (action: ToggleActiveAction | undefined) => {
          if (!action) return;
          const nonRevokedTokens = selectedTokens.filter((t) => !t.revoked);
          const tokensToProcess =
            action === "activate"
              ? nonRevokedTokens.filter((t) => !t.active)
              : action === "deactivate"
                ? nonRevokedTokens.filter((t) => t.active)
                : nonRevokedTokens;
          if (tokensToProcess.length === 0) {
            this.notificationService.success($localize`:@@token.noTokensProcess:No tokens to process.`);
            return;
          }
          from(tokensToProcess)
            .pipe(
              concatMap((token) => {
                const shouldDisable = action === "deactivate" ? true : action === "activate" ? false : token.active;
                return this.tokenService.toggleActive(token.serial, shouldDisable);
              }),
              reduce(() => null, null)
            )
            .subscribe({
              next: () => {
                this.notificationService.success(this.toggleSuccessMessage(action, tokensToProcess.length));
                this.tokenService.tokenResource.reload();
              },
              error: (err) => {
                let message = $localize`:@@token.errorOccurredWhileToggling:An error occurred while toggling tokens.`;
                if (err.error?.result?.error?.message) {
                  message = err.error.result.error.message;
                }
                this.notificationService.error(message);
                this.tokenService.tokenResource.reload();
              }
            });
        }
      });
  }

  resetFailcounterSelectedTokens(): void {
    const selectedTokens = this.tokenSelection.selectedRows();
    if (selectedTokens.length === 0) return;
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`:@@token.resetFailcounter:Reset Failcounter for Selected Tokens`,
          items: selectedTokens.map((token) => token.serial),
          itemType: $localize`:@@common.itemTypeToken:token`,
          confirmAction: { label: $localize`:@@common.reset:Reset`, value: true, type: "confirm" }
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            from(selectedTokens)
              .pipe(
                concatMap((token) => this.tokenService.resetFailCount(token.serial)),
                reduce(() => null, null)
              )
              .subscribe({
                next: () => {
                  this.notificationService.success(
                    pluralize(this.localeId, selectedTokens.length, {
                      one: $localize`:@@token.successfullyResetOne:Successfully reset the failcounter for 1 token.`,
                      few: $localize`:@@token.successfullyResetFew:Successfully reset the failcounter for ${selectedTokens.length}:COUNT: tokens.`,
                      many: $localize`:@@token.successfullyResetMany:Successfully reset the failcounter for ${selectedTokens.length}:COUNT: tokens.`,
                      other: $localize`:@@token.successfullyResetOther:Successfully reset the failcounter for ${selectedTokens.length}:COUNT: tokens.`
                    })
                  );
                  this.tokenService.tokenResource.reload();
                  this.tokenService.tokenDetailResource.reload();
                },
                error: (err) => {
                  let message = $localize`:@@token.errorOccurredWhile:An error occurred while resetting failcounters.`;
                  if (err.error?.result?.error?.message) {
                    message = err.error.result.error.message;
                  }
                  this.notificationService.error(message);
                  this.tokenService.tokenResource.reload();
                }
              });
          }
        }
      });
  }

  assignSelectedTokens() {
    this.dialogService
      .openDialog({ component: SelectedUserAssignDialogComponent })
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap((result) =>
          from(this.tokenSelection.selectedRows()).pipe(
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
          let message = $localize`:@@token.errorOccurred:An error occurred while assigning tokens.`;
          if (err.error?.result?.error?.message) {
            message = err.error.result.error.message;
          }
          this.notificationService.error(message);
          return EMPTY;
        })
      )
      .subscribe();
  }

  unassignSelectedTokens() {
    const selectedTokens = this.tokenSelection.selectedRows();
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`:@@token.unassignSelected:Unassign Selected Tokens`,
          items: selectedTokens.map((token) => token.serial),
          itemType: $localize`:@@common.itemTypeToken:token`,
          confirmAction: { label: $localize`:@@common.unassign:Unassign`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.tokenService.bulkUnassignTokens(selectedTokens).subscribe({
              next: (response: PiResponse<BulkResult>) => {
                const failedTokens = response.result?.value?.failed || [];
                const unauthorizedTokens = response.result?.value?.unauthorized || [];
                const count_success = response.result?.value?.count_success || 0;
                const messages: string[] = [];

                if (count_success) {
                  messages.push(
                    pluralize(this.localeId, count_success, {
                      one: $localize`:@@token.successfullyUnassignedOne:Successfully unassigned 1 token.`,
                      few: $localize`:@@token.successfullyUnassignedFew:Successfully unassigned ${count_success}:COUNT: tokens.`,
                      many: $localize`:@@token.successfullyUnassignedMany:Successfully unassigned ${count_success}:COUNT: tokens.`,
                      other: $localize`:@@token.successfullyUnassignedOther:Successfully unassigned ${count_success}:COUNT: tokens.`
                    })
                  );
                }

                if (failedTokens.length > 0) {
                  messages.push(
                    $localize`:@@token.followingTokensFailed:The following tokens failed to unassign: ${formatList(this.localeId, failedTokens)}:TOKENS:`
                  );
                }

                if (unauthorizedTokens.length > 0) {
                  messages.push(
                    $localize`:@@token.youNotAuthorized:You are not authorized to unassign the following tokens: ${formatList(this.localeId, unauthorizedTokens)}:TOKENS:`
                  );
                }

                if (messages.length > 0) {
                  this.notificationService.success(messages.join("\n"));
                }
                this.tokenService.tokenResource.reload();
              },
              error: (err) => {
                let message = $localize`:@@token.errorOccurredWhileUnassigning:An error occurred while unassigning tokens.`;
                if (err.error?.result?.error?.message) {
                  message = err.error.result.error.message;
                }
                this.notificationService.error(message);
              }
            });
          }
        }
      });
  }

  isFilterSelected(filter: string): boolean {
    const inputValue = this.tokenService.activeFilter();
    if (filter === "infokey & infovalue") {
      return inputValue.hasKey("infokey") && inputValue.hasKey("infovalue");
    }
    return inputValue.hasKey(filter);
  }

  getFilterIconName(keyword: string): string {
    if (keyword === "active" || keyword === "assigned") {
      const value = this.tokenService.activeFilter().booleanValueOfKey(keyword);
      if (value === undefined) {
        return "filter_alt";
      }
      return value ? "screen_rotation_alt" : "filter_alt_off";
    } else {
      const isSelected = this.isFilterSelected(keyword);
      return isSelected ? "filter_alt_off" : "filter_alt";
    }
  }

  onAdvancedFilterClick(filterKeyword: string): void {
    this.toggleFilter(filterKeyword);
    setTimeout(() => {
      const elementById = this.document.getElementById("token-filter-input") as HTMLInputElement | null;
      elementById?.focus();
    });
  }

  private toggleFilter(filterKeyword: string): void {
    this.tokenService.updateFilter((current) => this.toggledFilter(filterKeyword, current));
  }

  private toggledFilter(filterKeyword: string, current: FilterValue): FilterValue {
    let newValue;
    if (filterKeyword === "assigned") {
      newValue = this.tableUtilsService.toggleBooleanInFilter({
        keyword: filterKeyword,
        currentValue: current
      });
    } else if (filterKeyword === "infokey & infovalue") {
      const hasKey = current.hasKey("infokey");
      const hasVal = current.hasKey("infovalue");

      if (hasKey && hasVal) {
        newValue = this.tableUtilsService.toggleKeywordInFilter({
          keyword: "infokey",
          currentValue: current
        });
        newValue = this.tableUtilsService.toggleKeywordInFilter({
          keyword: "infovalue",
          currentValue: newValue
        });
      } else if (!hasKey && !hasVal) {
        newValue = this.tableUtilsService.toggleKeywordInFilter({
          keyword: "infokey",
          currentValue: current
        });
        newValue = this.tableUtilsService.toggleKeywordInFilter({
          keyword: "infovalue",
          currentValue: newValue
        });
      } else if (hasKey && !hasVal) {
        newValue = this.tableUtilsService.toggleKeywordInFilter({
          keyword: "infovalue",
          currentValue: current
        });
      } else {
        newValue = this.tableUtilsService.toggleKeywordInFilter({
          keyword: "infokey",
          currentValue: current
        });
      }
    } else {
      newValue = this.tableUtilsService.toggleKeywordInFilter({
        keyword: filterKeyword,
        currentValue: current
      });
    }
    return newValue;
  }

  private toggleSuccessMessage(action: ToggleActiveAction, count: number): string {
    switch (action) {
      case "activate":
        return pluralize(this.localeId, count, {
          one: $localize`:@@token.successfullyActivatedOne:Successfully activated 1 token.`,
          few: $localize`:@@token.successfullyActivatedFew:Successfully activated ${count}:COUNT: tokens.`,
          many: $localize`:@@token.successfullyActivatedMany:Successfully activated ${count}:COUNT: tokens.`,
          other: $localize`:@@token.successfullyActivatedOther:Successfully activated ${count}:COUNT: tokens.`
        });
      case "deactivate":
        return pluralize(this.localeId, count, {
          one: $localize`:@@token.successfullyDeactivatedOne:Successfully deactivated 1 token.`,
          few: $localize`:@@token.successfullyDeactivatedFew:Successfully deactivated ${count}:COUNT: tokens.`,
          many: $localize`:@@token.successfullyDeactivatedMany:Successfully deactivated ${count}:COUNT: tokens.`,
          other: $localize`:@@token.successfullyDeactivatedOther:Successfully deactivated ${count}:COUNT: tokens.`
        });
      default:
        return pluralize(this.localeId, count, {
          one: $localize`:@@token.successfullyToggledOne:Successfully toggled 1 token.`,
          few: $localize`:@@token.successfullyToggledFew:Successfully toggled ${count}:COUNT: tokens.`,
          many: $localize`:@@token.successfullyToggledMany:Successfully toggled ${count}:COUNT: tokens.`,
          other: $localize`:@@token.successfullyToggledOther:Successfully toggled ${count}:COUNT: tokens.`
        });
    }
  }
}
