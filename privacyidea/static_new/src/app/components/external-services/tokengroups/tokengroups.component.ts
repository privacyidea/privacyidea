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
import { Component, computed, ElementRef, inject, signal, ViewChild, WritableSignal } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatIconModule } from "@angular/material/icon";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { MatPaginator } from "@angular/material/paginator";
import { MatSort, MatSortModule } from "@angular/material/sort";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { MatTooltipModule } from "@angular/material/tooltip";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { Tokengroup, TokengroupService, TokengroupServiceInterface } from "@services/tokengroup/tokengroup.service";

@Component({
  selector: "app-tokengroups",
  standalone: true,
  imports: [
    MatTableModule,
    MatPaginator,
    MatSortModule,
    MatIconModule,
    MatButtonModule,
    MatCheckboxModule,
    MatTooltipModule,
    ScrollToTopDirective,
    MatFormField,
    MatLabel,
    ClearableInputComponent,
    MatInput,
    CopyableComponent
  ],
  templateUrl: "./tokengroups.component.html",
  styleUrl: "./tokengroups.component.scss"
})
export class TokengroupsComponent {
  protected readonly tokengroupService: TokengroupServiceInterface = inject(TokengroupService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  private readonly router = inject(Router);

  filterString = signal<string>("");
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  totalLength: WritableSignal<number> = computed(
    () => this.tokengroupService.tokengroups().length
  ) as WritableSignal<number>;

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild("filterHTMLInputElement", { static: false }) filterInput!: ElementRef;

  displayedColumns: string[] = ["select", "id", "groupname", "description"];

  selection = signal<Tokengroup[]>([]);

  tokengroupDataSource = computed(() => {
    const groups = this.tokengroupService.tokengroups();
    const dataSource = new MatTableDataSource(groups);
    dataSource.paginator = this.paginator;
    dataSource.sort = this.sort;
    return dataSource;
  });

  onCreateNewTokengroup(): void {
    this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_TOKENGROUPS_NEW);
  }

  onEditTokengroup(group: Tokengroup): void {
    this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_TOKENGROUPS_DETAILS + group.groupname);
  }


  isAllSelected(): boolean {
    const rows = this.tokengroupDataSource().data;
    return rows.length > 0 && this.selection().length === rows.length;
  }

  toggleAllRows(): void {
    if (this.isAllSelected()) {
      this.selection.set([]);
    } else {
      this.selection.set([...this.tokengroupDataSource().data]);
    }
  }

  toggleRow(row: Tokengroup): void {
    const current = this.selection();
    if (current.includes(row)) {
      this.selection.set(current.filter((selected) => selected !== row));
    } else {
      this.selection.set([...current, row]);
    }
  }

  isSelected(row: Tokengroup): boolean {
    return this.selection().includes(row);
  }

  deleteSelected(): void {
    const selected = this.selection();
    if (selected.length === 0) {
      return;
    }
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`Delete Token Groups`,
          items: selected.map((row) => row.groupname),
          itemType: "tokengroup",
          confirmAction: { label: $localize`Delete`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result) {
          selected.forEach((row) => this.tokengroupService.deleteTokengroup(row.groupname));
          this.selection.set([]);
        }
      });
  }


  onFilterInput(value: string): void {
    const trimmed = (value ?? "").trim();
    this.filterString.set(trimmed);

    const ds = this.tokengroupDataSource();
    ds.filter = trimmed.toLowerCase();
  }

  resetFilter(): void {
    this.filterString.set("");
    const ds = this.tokengroupDataSource();
    ds.filter = "";
    const inputEl = this.filterInput?.nativeElement as HTMLInputElement | undefined;
    if (inputEl) {
      inputEl.value = "";
    }
  }
}
