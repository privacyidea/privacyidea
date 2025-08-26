import { AuditService, AuditServiceInterface } from "../../../../services/audit/audit.service";
import { Component, inject, signal } from "@angular/core";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { EMPTY, catchError, concatMap, filter, forkJoin, from, reduce, switchMap } from "rxjs";
import { MatList, MatListItem } from "@angular/material/list";
import { Router, RouterLink } from "@angular/router";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { VersioningService, VersioningServiceInterface } from "../../../../services/version/version.service";

import { ConfirmationDialogComponent } from "../../../shared/confirmation-dialog/confirmation-dialog.component";
import { FilterValue } from "../../../../core/models/filter_value";
import { LostTokenComponent } from "./lost-token/lost-token.component";
import { MatButton } from "@angular/material/button";
import { MatDialog } from "@angular/material/dialog";
import { MatDivider } from "@angular/material/divider";
import { MatIcon } from "@angular/material/icon";
import { NgClass } from "@angular/common";
import { ROUTE_PATHS } from "../../../../app.routes";
import { SelectedUserAssignDialogComponent } from "../selected-user-assign-dialog/selected-user-assign-dialog.component";
import { tabToggleState } from "../../../../../styles/animations/animations";
import { tap } from "rxjs/operators";

@Component({
  selector: "app-token-tab",
  standalone: true,
  imports: [MatIcon, MatList, MatListItem, MatButton, MatDivider, NgClass, RouterLink],
  templateUrl: "./token-tab.component.html",
  styleUrl: "./token-tab.component.scss",
  animations: [tabToggleState]
})
export class TokenTabComponent {
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly dialog: MatDialog = inject(MatDialog);
  protected readonly auditService: AuditServiceInterface = inject(AuditService);
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
          serial_list: [this.tokenSerial()],
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
          serial_list: [this.tokenSerial()],
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
          serial_list: selectedTokens.map((token) => token.serial),
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
            forkJoin(selectedTokens.map((token) => this.tokenService.deleteToken(token.serial))).subscribe({
              next: () => {
                this.tokenService.tokenResource.reload();
              },
              error: (err) => {
                console.error("Error deleting tokens:", err);
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
          console.error("Error assigning tokens:", err);
          return EMPTY;
        })
      )
      .subscribe();
  }

  onClickManageSearch(): void {
    this.auditService.auditFilter.set(new FilterValue({ value: `serial: ${this.tokenSerial()}` }));
  }
}
