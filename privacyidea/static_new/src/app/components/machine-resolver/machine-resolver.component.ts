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

import { Component, computed, inject, linkedSignal, signal, viewChild, WritableSignal } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatPaginator } from "@angular/material/paginator";
import { MatSort, MatSortModule } from "@angular/material/sort";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { MatTooltipModule } from "@angular/material/tooltip";
import { Router, RouterLink } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { TableStateComponent } from "@components/shared/table-state/table-state.component";
import { TableState } from "@core/models/table_state/table-state";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import {
  MachineResolver,
  MachineResolverService,
  MachineResolverServiceInterface
} from "@services/machine-resolver/machine-resolver.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { lastValueFrom } from "rxjs";

const columnKeysMap = [
  { key: "resolvername", label: $localize`:@@common.name:Name` },
  { key: "type", label: $localize`:@@common.type:Type` }
];

@Component({
  selector: "app-machine-resolver",
  templateUrl: "./machine-resolver.component.html",
  styleUrls: ["./machine-resolver.component.scss"],
  standalone: true,
  imports: [
    MatTableModule,

    MatSortModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    ClearableInputComponent,
    ScrollToTopDirective,
    RouterLink,
    TableStateComponent
  ]
})
export class MachineResolverComponent {
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  protected readonly columnKeysMap = columnKeysMap;
  readonly columnKeys: string[] = this.columnKeysMap.map((column) => column.key);

  readonly machineResolverService: MachineResolverServiceInterface = inject(MachineResolverService);
  readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);
  private readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);

  paginator = viewChild(MatPaginator);
  sort = viewChild(MatSort);

  filterString = signal<string>("");

  readonly tableState = new TableState({
    resource: this.machineResolverService.machineResolverResource,
    count: () => this.machineResolverService.machineResolvers().length,
    allowed: () => this.authService.actionAllowed("mresolverread"),
    resetFilter: () => this.resetFilter()
  });
  readonly emptyHint = computed(() =>
    this.authService.actionAllowed("mresolverwrite")
      ? $localize`Create a machine resolver to read machines from a machine store.`
      : ""
  );

  machineResolversDataSource: WritableSignal<MatTableDataSource<MachineResolver>> = linkedSignal({
    source: () => ({
      machineResolvers: this.machineResolverService.machineResolvers(),
      paginator: this.paginator(),
      sort: this.sort()
    }),
    computation: (source) => {
      const dataSource = new MatTableDataSource(source.machineResolvers ?? []);
      dataSource.paginator = source.paginator ?? null;
      dataSource.sort = source.sort ?? null;

      dataSource.filterPredicate = (data: MachineResolver, filter: string) => {
        const normalizedFilter = filter.trim().toLowerCase();
        if (!normalizedFilter) {
          return true;
        }
        return (
          data.resolvername.toLowerCase().includes(normalizedFilter) ||
          data.type.toLowerCase().includes(normalizedFilter)
        );
      };

      dataSource.filter = this.filterString().trim().toLowerCase();
      return dataSource;
    }
  });

  onFilterInput(value: string): void {
    this.filterString.set(value);
    this.machineResolversDataSource().filter = value.trim().toLowerCase();
  }

  resetFilter(): void {
    this.filterString.set("");
    this.machineResolversDataSource().filter = "";
  }

  onNewMachineResolver(): void {
    this.router.navigateByUrl(ROUTE_PATHS.MACHINE_RESOLVER_NEW);
  }

  async onDeleteMachineResolver(machineResolver: MachineResolver): Promise<void> {
    const result = await lastValueFrom(
      this.dialogService
        .openDialog({
          component: SimpleConfirmationDialogComponent,
          data: {
            title: $localize`:@@machine.deleteMachine:Delete Machine Resolver`,
            items: [machineResolver.resolvername],
            itemType: "machine resolver",
            confirmAction: { label: $localize`:@@common.delete:Delete`, value: true, type: "destruct" }
          }
        })
        .afterClosed()
    );
    if (!result) {
      return;
    }
    try {
      await this.machineResolverService.deleteMachineResolver(machineResolver.resolvername);
    } catch {
      /* notification handled by the service */
    }
  }
}
