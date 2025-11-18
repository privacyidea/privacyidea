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
import { Component, computed, inject, linkedSignal, Signal, signal, ViewChild, WritableSignal } from "@angular/core";
import {
  MatCell,
  MatCellDef,
  MatColumnDef,
  MatFooterCell,
  MatFooterCellDef,
  MatFooterRow,
  MatFooterRowDef,
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
import { MatPaginator } from "@angular/material/paginator";
import { MatSort, MatSortModule } from "@angular/material/sort";
import { FormsModule } from "@angular/forms";
import { NgClass } from "@angular/common";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";

import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../services/table-utils/table-utils.service";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import {
  RealmRow,
  Realms,
  RealmService,
  RealmServiceInterface,
  ResolverGroup
} from "../../../services/realm/realm.service";
import { NodeInfo, SystemService, SystemServiceInterface } from "../../../services/system/system.service";
import { NotificationService, NotificationServiceInterface } from "../../../services/notification/notification.service";
import { HttpErrorResponse } from "@angular/common/http";
import { take } from "rxjs/operators";
import { ConfirmationDialogComponent } from "../../shared/confirmation-dialog/confirmation-dialog.component";
import { MatDialog } from "@angular/material/dialog";

const columnKeysMap = [
  { key: "name", label: "Realm" },
  { key: "isDefault", label: "Default" },
  { key: "resolvers", label: "Resolvers" },
  { key: "actions", label: "Actions" }
];

const ALL_NODES_VALUE = "__all_nodes__";

@Component({
  selector: "app-realm-table",
  standalone: true,
  imports: [
    FormsModule,
    MatCell,
    MatCellDef,
    MatFormField,
    MatInput,
    MatLabel,
    MatPaginator,
    MatTable,
    MatSortModule,
    MatHeaderCell,
    MatColumnDef,
    NgClass,
    MatHeaderRowDef,
    MatHeaderRow,
    MatRowDef,
    MatRow,
    MatNoDataRow,
    MatHeaderCellDef,
    ScrollToTopDirective,
    ClearableInputComponent,
    MatSelectModule,
    MatIconModule,
    MatButtonModule,
    MatFooterRowDef,
    MatFooterRow,
    MatFooterCellDef,
    MatFooterCell
  ],
  templateUrl: "./realm-table.component.html",
  styleUrl: "./realm-table.component.scss"
})
export class RealmTableComponent {
  protected readonly columnKeysMap = columnKeysMap;
  readonly columnKeys: string[] = this.columnKeysMap.map((column) => column.key);

  private readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly dialog: MatDialog = inject(MatDialog);

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  pageSizeOptions = this.tableUtilsService.pageSizeOptions;

  selectedNode = signal<string>(ALL_NODES_VALUE);
  filterString = signal<string>("");

  nodeOptions = computed(() => {
    const nodes = this.systemService.nodes();
    return [
      { label: $localize`All nodes`, value: ALL_NODES_VALUE },
      ...nodes.map((n: NodeInfo) => ({
        label: n.name,
        value: n.uuid
      }))
    ];
  });

  newRealmName = signal<string>("");
  newRealmNodeId = signal<string>("");
  newRealmResolvers = signal<string[]>([]);
  isCreatingRealm = signal<boolean>(false);
  editingRealmName = signal<string | null>(null);
  editRealmNodeId = signal<string>("");
  editRealmResolvers = signal<string[]>([]);
  isSavingEditedRealm = signal<boolean>(false);

  createNodeOptions = computed(() => {
    const nodes = this.systemService.nodes();
    return [
      { label: $localize`No node`, value: "" },
      ...nodes.map((n: NodeInfo) => ({
        label: n.name,
        value: n.uuid
      }))
    ];
  });

  resolverOptions = computed(() => {
    const realmResource = this.realmService.realmResource.value();
    const realms = realmResource?.result?.value;
    if (!realms) {
      return [];
    }
    const map = new Map<string, string>();
    Object.values(realms).forEach((realm: any) => {
      (realm.resolver ?? []).forEach((r: any) => {
        if (!map.has(r.name)) {
          map.set(r.name, r.type);
        }
      });
    });
    return Array.from(map.entries()).map(([name, type]) => ({ name, type }));
  });

  realmRows = computed<RealmRow[]>(() => {
    const realmResource = this.realmService.realmResource.value();
    const realms: Realms | undefined = realmResource?.result?.value as Realms | undefined;
    if (!realms) {
      return [];
    }

    const nodes = this.systemService.nodes();
    const selectedNodeUuid = this.selectedNode();

    return Object.entries(realms).flatMap(([realmName, realm]) => {
      const resolvers = realm.resolver ?? [];

      if (selectedNodeUuid !== ALL_NODES_VALUE) {
        const matchesNode = resolvers.some((r: { node: string }) => r.node === selectedNodeUuid);
        if (!matchesNode) {
          return [];
        }
      }

      const groupsMap = new Map<string, ResolverGroup>();

      for (const r of resolvers) {
        const nodeKey = r.node || "__no_node__";

        if (!groupsMap.has(nodeKey)) {
          let nodeLabel: string;
          if (!r.node) {
            nodeLabel = $localize`No node`;
          } else {
            const nodeInfo = nodes.find((n) => n.uuid === r.node || n.name === r.node);
            nodeLabel = nodeInfo?.name ?? r.node;
          }

          groupsMap.set(nodeKey, {
            nodeId: r.node ?? "",
            nodeLabel,
            resolvers: []
          });
        }

        groupsMap.get(nodeKey)!.resolvers.push({
          name: r.name,
          type: r.type,
          priority: r.priority
        });
      }

      const resolverGroups = Array.from(groupsMap.values());

      const resolversText = resolverGroups
        .flatMap((g) =>
          g.resolvers.map(
            (rr) => `${rr.name} ${rr.type} ${g.nodeLabel} ${rr.priority ?? ""}`
          )
        )
        .join(" ");

      return [
        {
          name: realmName,
          isDefault: realm.default,
          resolverGroups,
          resolversText,
          isCreateRow: false
        } as RealmRow
      ];
    });
  });

  totalLength: Signal<number> = computed(() => this.realmRows().length);

  realmsDataSource: WritableSignal<MatTableDataSource<RealmRow>> = linkedSignal({
    source: this.realmRows,
    computation: (rows, previous) => {
      const dataSource = new MatTableDataSource(rows ?? []);
      dataSource.paginator = this.paginator;
      dataSource.sort = this.sort;

      dataSource.filterPredicate = (data: RealmRow, filter: string) => {
        const normalizedFilter = filter.trim().toLowerCase();
        if (!normalizedFilter) {
          return true;
        }
        return (
          data.name.toLowerCase().includes(normalizedFilter) ||
          data.resolversText.toLowerCase().includes(normalizedFilter)
        );
      };

      dataSource.filter = this.filterString().trim().toLowerCase();
      return dataSource;
    }
  });

  onFilterInput(value: string): void {
    this.filterString.set(value);
    const ds = this.realmsDataSource();
    ds.filter = value.trim().toLowerCase();
  }

  resetFilter(): void {
    this.filterString.set("");
    const ds = this.realmsDataSource();
    ds.filter = "";
  }

  onNodeSelectionChange(value: string): void {
    this.selectedNode.set(value);
  }

  onNewRealmResolversChange(values: string[]): void {
    this.newRealmResolvers.set(values);
  }

  canSubmitNewRealm(): boolean {
    return (
      this.newRealmName().trim().length > 0 &&
      !this.isCreatingRealm()
    );
  }

  resetCreateForm(): void {
    this.newRealmName.set("");
    this.newRealmNodeId.set("");
    this.newRealmResolvers.set([]);
  }

  onCreateRealm(): void {
    if (!this.canSubmitNewRealm()) {
      return;
    }

    this.isCreatingRealm.set(true);

    const realmName = this.newRealmName().trim();
    const nodeId = this.newRealmNodeId();
    const resolvers = this.newRealmResolvers().map((name, index) => ({
      name,
      priority: index + 1
    }));

    this.realmService
      .createRealm(realmName, nodeId, resolvers)
      .pipe(take(1))
      .subscribe({
        next: () => {
          this.notificationService.openSnackBar($localize`Realm created.`);
          this.resetCreateForm();
          this.realmService.realmResource.reload?.();
        },
        error: (err: HttpErrorResponse) => {
          console.error("Failed to create realm.", err);
          const message = err.error?.result?.error?.message || err.message;
          this.notificationService.openSnackBar(
            $localize`Failed to create realm. ${message}`
          );
        }
      })
      .add(() => this.isCreatingRealm.set(false));
  }

  onEditRealm(row: RealmRow): void {
    console.log("Edit realm", row.name);
    // TODO: open edit dialog, or inline editing
  }

  onDeleteRealm(row: RealmRow): void {
    if (!row?.name) {
      return;
    }

    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serialList: [row.name],
          title: $localize`Delete Realm`,
          type: "realm",
          action: "delete"
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (!result) {
            return;
          }

          this.realmService
            .deleteRealm(row.name)
            .subscribe({
              next: () => {
                this.notificationService.openSnackBar(
                  $localize`Realm "${row.name}" deleted.`
                );
                this.realmService.realmResource.reload?.();
              },
              error: (err: HttpErrorResponse) => {
                console.error("Failed to delete realm.", err);
                const message = err.error?.result?.error?.message || err.message;
                this.notificationService.openSnackBar(
                  $localize`Failed to delete realm. ${message}`
                );
              }
            });
        }
      });
  }

  startEditRealm(row: RealmRow): void {
    if (!row?.name) {
      return;
    }

    this.editingRealmName.set(row.name);

    const firstGroup = row.resolverGroups[0];
    if (firstGroup) {
      this.editRealmNodeId.set(firstGroup.nodeId ?? "");
      this.editRealmResolvers.set(firstGroup.resolvers.map((r) => r.name));
    } else {
      this.editRealmNodeId.set("");
      this.editRealmResolvers.set([]);
    }
  }

  cancelEditRealm(): void {
    this.editingRealmName.set(null);
    this.editRealmNodeId.set("");
    this.editRealmResolvers.set([]);
    this.isSavingEditedRealm.set(false);
  }

  onEditRealmResolversChange(values: string[]): void {
    this.editRealmResolvers.set(values);
  }

  canSaveEditedRealm(row: RealmRow): boolean {
    return (
      this.editingRealmName() === row.name &&
      !this.isSavingEditedRealm()
    );
  }

  saveEditedRealm(row: RealmRow): void {
    if (this.editingRealmName() !== row.name) {
      return;
    }

    this.isSavingEditedRealm.set(true);

    const realmName = row.name;
    const rawNodeId = this.editRealmNodeId();
    const nodeId =
      rawNodeId && rawNodeId.length > 0
        ? rawNodeId
        : "00000000-0000-0000-0000-000000000000"; // "no node"

    const resolvers =
      this.editRealmResolvers().length > 0
        ? this.editRealmResolvers().map((name, index) => ({
          name,
          priority: index + 1
        }))
        : [];

    this.realmService
      .createRealm(realmName, nodeId, resolvers)
      .pipe(take(1))
      .subscribe({
        next: () => {
          this.notificationService.openSnackBar(
            $localize`Realm "${realmName}" updated.`
          );
          this.cancelEditRealm();
          this.realmService.realmResource.reload?.();
        },
        error: (err: HttpErrorResponse) => {
          console.error("Failed to update realm.", err);
          const message = err.error?.result?.error?.message || err.message;
          this.notificationService.openSnackBar(
            $localize`Failed to update realm. ${message}`
          );
        }
      })
      .add(() => this.isSavingEditedRealm.set(false));
  }
}
