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
import { DatePipe, NgClass, TitleCasePipe } from "@angular/common";
import { Component, inject, linkedSignal, signal, WritableSignal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { MatTooltipModule } from "@angular/material/tooltip";
import { Sort } from "@angular/material/sort";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { ScrollEdgesDirective } from "@components/shared/directives/scroll-edges.directive";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import {
  BlocklistEntry,
  ConditionalAccessStateService,
  ConditionalAccessStateServiceInterface
} from "@services/conditional-access-state/conditional-access-state.service";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { from } from "rxjs";
import { concatMap, reduce } from "rxjs/operators";

@Component({
  selector: "app-blocklist",
  templateUrl: "./blocklist.component.html",
  styleUrl: "./blocklist.component.scss",
  imports: [
    ScrollToTopDirective,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatCheckboxModule,
    MatFormField,
    MatLabel,
    MatHint,
    MatInput,
    ClearableInputComponent,
    ScrollEdgesDirective,
    DatePipe,
    TitleCasePipe,
    NgClass
  ]
})
export class BlocklistComponent {
  protected readonly casService: ConditionalAccessStateServiceInterface = inject(ConditionalAccessStateService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;

  readonly displayedColumns: string[] = ["select", "identifier", "state", "block_expires_at", "reason", "last_updated"];

  // Keep the previous rows while a reload is in flight to avoid flicker.
  readonly dataSource = linkedSignal<PiResponse<BlocklistEntry[]> | undefined, MatTableDataSource<BlocklistEntry>>({
    source: () =>
      this.casService.blocklistResource.hasValue() ? this.casService.blocklistResource.value() : undefined,
    computation: (resource, previous) => {
      if (resource) {
        const ds = new MatTableDataSource(this.sortRows(resource.result?.value ?? []));
        ds.filterPredicate = this.blockFilterPredicate();
        return ds;
      }
      return previous?.value ?? new MatTableDataSource<BlocklistEntry>([]);
    }
  });

   // Selection resets whenever the underlying data changes.
   readonly selection = linkedSignal<PiResponse<BlocklistEntry[]> | undefined, BlocklistEntry[]>({
     source: () =>
       this.casService.blocklistResource.hasValue() ? this.casService.blocklistResource.value() : undefined,
     computation: () => []
   });

   filterText = "";
   readonly sort: WritableSignal<Sort> = signal({ active: "identifier", direction: "asc" });

  blockState(row: BlocklistEntry): string {
    if (row.permanent) {
      return "permanent";
    }
    return (row.seconds_remaining ?? 0) === 0 ? "expired" : "temporary";
  }

  blockFilterPredicate() {
    return (element: BlocklistEntry, filterValue: string): boolean => {
      if (!filterValue) {
        return true;
      }

      const lowerFilter = filterValue.toLowerCase();
      return (
        element.identifier.toLowerCase().includes(lowerFilter) ||
        (element.reason?.toLowerCase().includes(lowerFilter) ?? false) ||
        element.last_updated.toLowerCase().includes(lowerFilter) ||
        this.blockState(element).toLowerCase().includes(lowerFilter)
      );
    };
  }

  isExpired(row: BlocklistEntry): boolean {
    return !row.permanent && (row.seconds_remaining ?? 0) === 0;
  }

  blockStateClass(row: BlocklistEntry): string {
    if (row.permanent) {
      return "highlight-false";
    }
    return this.isExpired(row) ? "highlight-true" : "highlight-warning";
  }

  onSortEvent(columnKey: string): void {
    const current = this.sort();
    let direction: Sort["direction"] = "asc";

    if (current.active === columnKey) {
      if (current.direction === "asc") {
        direction = "desc";
      } else if (current.direction === "desc") {
        direction = "";
      }
    }

    this.sort.set(direction ? { active: columnKey, direction } : { active: "identifier", direction: "asc" });
    const ds = this.dataSource();
    ds.data = this.sortRows([...ds.data]);
    ds.filter = this.filterText;
  }

  getSortIcon(columnKey: string): string {
    const current = this.sort();
    if (current.active !== columnKey || !current.direction) {
      return "unfold_more";
    }
    return current.direction === "asc" ? "keyboard_arrow_upward" : "keyboard_arrow_downward";
  }

  private sortRows(rows: BlocklistEntry[]): BlocklistEntry[] {
    const { active, direction } = this.sort();
    if (!direction) {
      return rows;
    }

    const sortedRows = [...rows];
    const dir = direction === "asc" ? 1 : -1;
    sortedRows.sort((a, b) =>
      this.compareValues(this.sortValueForKey(a, active), this.sortValueForKey(b, active), dir)
    );
    return sortedRows;
  }

  private sortValueForKey(row: BlocklistEntry, key: string): string | number {
    switch (key) {
      case "state":
        return this.blockState(row);
      case "block_expires_at":
      case "last_updated": {
        const timestamp = Date.parse(String((row as unknown as Record<string, unknown>)[key] ?? ""));
        return Number.isNaN(timestamp) ? "" : timestamp;
      }
      default:
        return String((row as unknown as Record<string, unknown>)[key] ?? "").toLowerCase();
    }
  }

  private compareValues(a: string | number, b: string | number, dir: 1 | -1): number {
    if (typeof a === "number" && typeof b === "number") {
      return (a - b) * dir;
    }
    if (a < b) return -1 * dir;
    if (a > b) return 1 * dir;
    return 0;
  }

  isAllSelected(): boolean {
    const rows = this.dataSource().data;
    return rows.length > 0 && this.selection().length === rows.length;
  }

  toggleAllRows(): void {
    this.selection.set(this.isAllSelected() ? [] : [...this.dataSource().data]);
  }

  toggleRow(row: BlocklistEntry): void {
    const current = this.selection();
    this.selection.set(current.includes(row) ? current.filter((r) => r !== row) : [...current, row]);
  }

  // --- filtering ---

  handleFilterInput(event: Event): void {
    this.filterText = (event.target as HTMLInputElement).value;
    this.dataSource().filter = this.filterText;
  }

  clearFilter(): void {
    this.filterText = "";
    this.dataSource().filter = "";
  }


  // --- bulk actions ---

  removeSelected(): void {
    const rows = this.selection();
    if (rows.length === 0) {
      return;
    }
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`Remove Blocklist Entries`,
          items: rows.map((row) => row.identifier),
          itemType: "blocklist entry",
          confirmAction: { label: $localize`Remove`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe((confirmed) => {
        if (!confirmed) {
          return;
        }
        from(rows)
          .pipe(
            concatMap((row) => this.casService.removeBlocklistEntry(row)),
            reduce((count, success) => count + (success ? 1 : 0), 0)
          )
          .subscribe((count) => {
            if (count > 0) {
              this.notificationService.success($localize`Removed ${count} blocklist entry(s).`);
            }
            this.casService.blocklistResource.reload();
          });
      });
  }

  cleanUpExpired(): void {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`Clean Up Expired Entries`,
          items: [],
          itemType: "expired blocklist entry",
          message: $localize`This permanently deletes all expired blocklist entries from the database.`,
          confirmAction: { label: $localize`Clean Up`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe((confirmed) => {
        if (!confirmed) {
          return;
        }
        this.casService.purgeBlocklist().subscribe((count) => {
          this.notificationService.success($localize`Deleted ${count} expired blocklist entry(s).`);
          this.casService.blocklistResource.reload();
        });
      });
  }

  protected readonly Array = Array;
}
