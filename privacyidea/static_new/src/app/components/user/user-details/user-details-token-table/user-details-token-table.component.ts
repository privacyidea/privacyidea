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
import { NgClass, NgTemplateOutlet } from "@angular/common";
import {
  Component,
  computed,
  effect,
  inject,
  input,
  linkedSignal,
  signal,
  TemplateRef,
  WritableSignal
} from "@angular/core";
import { toSignal } from "@angular/core/rxjs-interop";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatIcon } from "@angular/material/icon";
import { Sort } from "@angular/material/sort";
import {
  MatCell,
  MatCellDef,
  MatColumnDef,
  MatHeaderCell,
  MatHeaderCellDef,
  MatHeaderRow,
  MatHeaderRowDef,
  MatNoDataRow,
  MatRow,
  MatRowDef,
  MatTable,
  MatTableDataSource
} from "@angular/material/table";
import { MatTooltip } from "@angular/material/tooltip";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { TableStateComponent } from "@components/shared/table-state/table-state.component";
import { TableState } from "@core/models/table_state/table-state";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContainerDetailToken } from "@services/container/container.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { RowSelector } from "@services/table-utils/row-selector";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { TokenDetails, TokenService, TokenServiceInterface } from "@services/token/token.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";
import { catchError, forkJoin, map, Observable, of } from "rxjs";

interface BulkActionResult {
  serial: string;
  ok: boolean;
}

type BulkAction = "unassign" | "toggleActive" | "resetFailCount";

@Component({
  selector: "app-user-details-token-table",
  imports: [
    CopyableComponent,
    MatButton,
    MatCell,
    MatCellDef,
    MatCheckbox,
    MatColumnDef,
    MatHeaderCell,
    MatHeaderRow,
    MatHeaderRowDef,
    MatIcon,
    MatIconButton,
    MatRow,
    MatRowDef,
    MatTable,
    MatTooltip,
    NgClass,
    NgTemplateOutlet,
    MatHeaderCellDef,
    MatNoDataRow,
    TableStateComponent
  ],
  templateUrl: "./user-details-token-table.component.html",
  styleUrl: "./user-details-token-table.component.scss"
})
export class UserDetailsTokenTableComponent {

  protected linkLabel(label: string): string {
    return $localize`:@@common.linkLabel:${label}:LABEL: link`;
  }

  /**
   * The two ways out of the empty state. They are passed as templates rather than projected content
   * because this component renders them in a different place depending on the table's state, and a
   * single ng-content slot can only ever be rendered once.
   */
  readonly enrollAction = input<TemplateRef<unknown> | undefined>(undefined);
  readonly assignAction = input<TemplateRef<unknown> | undefined>(undefined);

  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  readonly columnsKeyMap = this.tableUtilsService.pickColumns(
    "serial",
    "tokentype",
    "active",
    "description",
    "failcount",
    "maxfail",
    "container_serial"
  );
  readonly columnKeys = [...this.tableUtilsService.getColumnKeys(this.columnsKeyMap)];

  get displayedColumns(): string[] {
    return ["select", ...this.columnsKeyMap.map((column) => column.key)];
  }

  dataSource = new MatTableDataSource<ContainerDetailToken>([]);
  sort = signal({ active: "serial", direction: "asc" } as Sort);
  apiFilterKeys = this.tokenService.apiFilterKeys;
  userTokenData: WritableSignal<MatTableDataSource<TokenDetails>> = linkedSignal({
    source: () =>
      this.tokenService.userTokenResource.hasValue() ? this.tokenService.userTokenResource.value() : undefined,
    computation: (userTokenResource, previous) => {
      if (!userTokenResource) {
        return previous?.value ?? new MatTableDataSource<TokenDetails>([]);
      }
      return new MatTableDataSource<TokenDetails>(userTokenResource.result?.value?.tokens ?? []);
    }
  });
  private readonly renderedRows = toSignal(this.dataSource.connect(), {
    initialValue: [] as ContainerDetailToken[]
  });

  selector = new RowSelector<ContainerDetailToken>({
    keyGetter: (row) => row.serial,
    visibleRows: this.renderedRows
  });

  readonly tableState = new TableState({
    resource: this.tokenService.userTokenResource,
    count: () => this.userTokenData().data.length,
    allowed: () => this.authService.actionAllowed("tokenlist")
  });

  /** Both routes out of the empty state are rights-gated, so the hint only offers the ones this admin has. */
  readonly emptyHint = computed(() => {
    const canEnroll = this.authService.tokenEnrollmentAllowed();
    const canAssign = this.authService.actionAllowed("assign");
    if (canEnroll && canAssign) {
      return $localize`:@@user.enrollNewTokenHint:Enroll a new token for this user, or assign an existing one.`;
    }
    if (canEnroll) {
      return $localize`:@@user.enrollNewTokenOnly:Enroll a new token for this user.`;
    }
    if (canAssign) {
      return $localize`:@@user.assignExistingToken:Assign an existing token to this user.`;
    }
    return "";
  });

  constructor() {
    effect(() => {
      if (!this.userTokenData) {
        return;
      }
      if (!this.tokenService.userTokenResource.hasValue()) {
        this.dataSource.data = [];
        return;
      }
      const base = this.userTokenData().data ?? [];
      this.dataSource.data = this.tableUtilsService.clientsideSortTokenData(
        base as unknown as ContainerDetailToken[],
        this.sort()
      );
    });

    effect(() => {
      const s = this.sort();
      this.dataSource.data = this.tableUtilsService.clientsideSortTokenData([...this.dataSource.data], s);
    });
  }

  deleteSelected(): void {
    const serials = this.selector.selectedRows().map((r) => r.serial);
    this.tokenService.bulkDeleteWithConfirmDialog(serials, () => this.tokenService.userTokenResource.reload());
  }

  unassignSelected(): void {
    const serials = this.selector.selectedRows().map((r) => r.serial);
    forkJoin(serials.map((s) => this.runBulkAction(s, this.tokenService.unassignUser(s, false)))).subscribe({
      next: (results) => this.finishBulkAction("unassign", results)
    });
  }

  toggleActiveSelected(): void {
    const rows = this.selector.selectedRows();
    forkJoin(
      rows.map((r) => this.runBulkAction(r.serial, this.tokenService.toggleActive(r.serial, r.active, false)))
    ).subscribe({
      next: (results) => this.finishBulkAction("toggleActive", results)
    });
  }

  resetFailcountSelected(): void {
    const serials = this.selector.selectedRows().map((r) => r.serial);
    forkJoin(serials.map((s) => this.runBulkAction(s, this.tokenService.resetFailCount(s, false)))).subscribe({
      next: (results) => this.finishBulkAction("resetFailCount", results)
    });
  }

  toggleActive(tokenDetails: TokenDetails): void {
    if (
      !tokenDetails.revoked &&
      !tokenDetails.locked &&
      ((tokenDetails.active && this.authService.actionAllowed("disable")) ||
        (!tokenDetails.active && this.authService.actionAllowed("enable")))
    ) {
      this.tokenService.toggleActive(tokenDetails.serial, tokenDetails.active).subscribe({
        next: () => this.tokenService.userTokenResource.reload()
      });
    }
  }

  resetFailCount(tokenDetails: TokenDetails): void {
    if (!tokenDetails.revoked && !tokenDetails.locked && this.authService.actionAllowed("reset")) {
      this.tokenService.resetFailCount(tokenDetails.serial).subscribe({
        next: () => this.tokenService.userTokenResource.reload()
      });
    }
  }

  private runBulkAction(serial: string, request: Observable<unknown>): Observable<BulkActionResult> {
    return request.pipe(
      map(() => ({ serial, ok: true })),
      catchError(() => of({ serial, ok: false }))
    );
  }

  private finishBulkAction(action: BulkAction, results: BulkActionResult[]): void {
    this.tokenService.userTokenResource.reload();
    const failed = results.filter((r) => !r.ok).map((r) => r.serial);
    if (failed.length > 0) {
      this.notificationService.error(this.bulkFailureMessage(action, failed, results.length));
    }
  }

  private bulkFailureMessage(action: BulkAction, failed: string[], total: number): string {
    const serials = failed.join(", ");
    switch (action) {
      case "unassign":
        return $localize`:@@user.bulkUnassignFailed:${failed.length}:COUNT:/${total}:TOTAL: unassign failed: ${serials}:SERIALS:`;
      case "toggleActive":
        return $localize`:@@user.bulkToggleActiveFailed:${failed.length}:COUNT:/${total}:TOTAL: toggle active failed: ${serials}:SERIALS:`;
      default:
        return $localize`:@@user.bulkResetFailCountFailed:${failed.length}:COUNT:/${total}:TOTAL: reset fail count failed: ${serials}:SERIALS:`;
    }
  }
}
