import { Component, inject, signal } from "@angular/core";
import { NgClass } from "@angular/common";
import { MatIcon } from "@angular/material/icon";
import { MatList, MatListItem } from "@angular/material/list";
import { MatButton } from "@angular/material/button";
import { MatDivider } from "@angular/material/divider";
import { MatDialog } from "@angular/material/dialog";
import { catchError, concatMap, EMPTY, filter, from, reduce, switchMap } from "rxjs";
import { tabToggleState } from "../../../../../styles/animations/animations";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { VersioningService, VersioningServiceInterface } from "../../../../services/version/version.service";
import { ConfirmationDialogComponent } from "../../../shared/confirmation-dialog/confirmation-dialog.component";
import { LostTokenComponent } from "./lost-token/lost-token.component";
import { Router, RouterLink } from "@angular/router";
import { AuditService, AuditServiceInterface } from "../../../../services/audit/audit.service";
import { SelectedUserAssignDialogComponent } from "../selected-user-assign-dialog/selected-user-assign-dialog.component";
import { tap } from "rxjs/operators";
import { ROUTE_PATHS } from "../../../../app.routes";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../services/notification/notification.service";
import { PiResponse } from "../../../../app.component";

interface BatchResult {
  failed: string[];
  unauthorized: string[];
}

@Component({
  selector: "app-token-tab",
  standalone: true,
  imports: [
    MatIcon,
    MatList,
    MatListItem,
    MatButton,
    MatDivider,
    NgClass,
    RouterLink
  ],
  templateUrl: "./token-tab.component.html",
  styleUrl: "./token-tab.component.scss",
  animations: [tabToggleState]
})
export class TokenTabComponent {
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly versioningService: VersioningServiceInterface =
    inject(VersioningService);
  protected readonly contentService: ContentServiceInterface =
    inject(ContentService);
  private readonly dialog: MatDialog = inject(MatDialog);
  protected readonly auditService: AuditServiceInterface = inject(AuditService);
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
    this.tokenService
      .toggleActive(this.tokenSerial(), this.tokenIsActive())
      .subscribe({
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
              .pipe(
                switchMap(() =>
                  this.tokenService.getTokenDetails(this.tokenSerial())
                )
              )
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
                this.router.navigateByUrl(ROUTE_PATHS.TOKENS);
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
          title: "Delete All Tokens",
          type: "token",
          action: "delete",
          numberOfTokens: selectedTokens.length
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.tokenService.batchDeleteTokens(selectedTokens).subscribe({
              next: (response: PiResponse<BatchResult, any>) => {
                const failedTokens = response.result?.value?.failed || [];
                const unauthorizedTokens = response.result?.value?.unauthorized || [];
                const messages: string[] = [];

                if (failedTokens.length > 0) {
                  messages.push(`The following tokens failed to delete: ${failedTokens.join(", ")}`);
                }

                if (unauthorizedTokens.length > 0) {
                  messages.push(`You are not authorized to delete the following tokens: ${unauthorizedTokens.join(", ")}`);
                }

                if (messages.length > 0) {
                  this.notificationService.openSnackBar(messages.join("\n"));
                }

                this.tokenService.tokenResource.reload();
              },
              error: (err) => {
                console.error("Error deleting tokens:", err);
                this.notificationService.openSnackBar("An error occurred while deleting tokens.");
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
                ? this.tokenService
                  .unassignUser(token.serial)
                  .pipe(switchMap(() => assign$))
                : assign$;
            }),
            reduce(() => null, null)
          )
        ),
        tap(() => this.tokenService.tokenResource.reload()),
        catchError((err) => {
          console.error("Error assigning tokens:", err);
          return EMPTY;
        })
      )
      .subscribe();
  }

  unassignSelectedTokens() {
    const selectedTokens = this.tokenSelection();
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serialList: selectedTokens.map((token) => token.serial),
          title: "Unassign Tokens",
          type: "token",
          action: "unassign",
          numberOfTokens: selectedTokens.length
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.tokenService.batchUnassignTokens(selectedTokens).subscribe({
              next: (response: PiResponse<BatchResult, any>) => {
                const failedTokens = response.result?.value?.failed || [];
                const unauthorizedTokens = response.result?.value?.unauthorized || [];
                const messages: string[] = [];

                if (failedTokens.length > 0) {
                  messages.push(`The following tokens failed to unassign: ${failedTokens.join(", ")}`);
                }

                if (unauthorizedTokens.length > 0) {
                  messages.push(`You are not authorized to unassign the following tokens: ${unauthorizedTokens.join(", ")}`);
                }

                if (messages.length > 0) {
                  this.notificationService.openSnackBar(messages.join("\n"));
                }
                this.tokenService.tokenResource.reload();
              },
              error: (err) => {
                console.error("Error unassigning tokens:", err);
                this.notificationService.openSnackBar("An error occurred while unassigning tokens.");
              }
            });
          }
        }
      });
  }
}
