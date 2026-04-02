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

import { NgClass } from "@angular/common";
import { HttpErrorResponse } from "@angular/common/http";
import {
  Component,
  inject,
  ViewChild,
  ElementRef,
  signal,
  computed,
  WritableSignal,
  linkedSignal
} from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatDialog } from "@angular/material/dialog";
import { MatIconModule } from "@angular/material/icon";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { MatPaginator } from "@angular/material/paginator";
import { MatSelectModule } from "@angular/material/select";
import { Sort } from "@angular/material/sort";
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
import { MatTooltip } from "@angular/material/tooltip";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { concat, last, take } from "rxjs";
import { AuthServiceInterface, AuthService } from "src/app/services/auth/auth.service";
import { ContentServiceInterface, ContentService } from "src/app/services/content/content.service";
import { DialogServiceInterface, DialogService } from "src/app/services/dialog/dialog.service";
import { NotificationServiceInterface, NotificationService } from "src/app/services/notification/notification.service";
import {
  RealmServiceInterface,
  RealmService,
  RealmRow,
  Realms,
  ResolverGroup
} from "src/app/services/realm/realm.service";
import { ResolverServiceInterface, ResolverService } from "src/app/services/resolver/resolver.service";
import { SystemServiceInterface, SystemService, NodeInfo } from "src/app/services/system/system.service";
import { TableUtilsServiceInterface, TableUtilsService } from "src/app/services/table-utils/table-utils.service";
import { UserNewResolverComponent } from "../user-new-resolver/user-new-resolver.component";

type ResolverWithPriority = { name: string; priority: number | null };
type NodeResolversMap = { [nodeId: string]: ResolverWithPriority[] };

const ALL_NODES_VALUE = "__all_nodes__";
const NO_NODE_ID = "";

const columnKeysMap = [
  { key: "name", label: "Realm" },
  { key: "isDefault", label: "Default" },
  { key: "resolvers", label: "Resolvers" },
  { key: "actions", label: "Actions" }
];

@Component({
  selector: "app-realm-table",
  standalone: true,
  imports: [
    ClearableInputComponent,
    FormsModule,
    MatButtonModule,
    MatCell,
    MatCellDef,
    MatColumnDef,
    MatFooterCell,
    MatFooterCellDef,
    MatFooterRow,
    MatFooterRowDef,
    MatFormField,
    MatHeaderCell,
    MatHeaderCellDef,
    MatHeaderRow,
    MatHeaderRowDef,
    MatIconModule,
    MatInput,
    MatLabel,
    MatNoDataRow,
    MatRow,
    MatRowDef,
    MatSelectModule,
    MatTable,
    MatTooltip,
    NgClass,
    ScrollToTopDirective
  ],
  templateUrl: "./realm-table.component.html",
  styleUrl: "./realm-table.component.scss"
})
export class RealmTableComponent {
  // Services
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly dialog = inject(MatDialog);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly resolverService: ResolverServiceInterface = inject(ResolverService);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  private readonly _notificationService: NotificationServiceInterface = inject(NotificationService);

  // View Children
  @ViewChild("filterHTMLInputElement", { static: false }) filterInput!: ElementRef<HTMLInputElement>;

  // Table Config
  protected readonly columnKeysMap = columnKeysMap;
  readonly columnKeys: string[] = this.columnKeysMap.map((column) => column.key);

  // Table State Signals
  selectedNode = signal<string>(ALL_NODES_VALUE);
  filterString = signal<string>("");
  sort = signal({ active: "name", direction: "asc" } as Sort);

  // Create Form State
  newRealmName = signal<string>("");
  newRealmNodeResolvers = signal<NodeResolversMap>({});
  isCreatingRealm = signal<boolean>(false);

  // Edit Form State
  editingRealmName = signal<string | null>(null);
  editOriginalNodeResolvers = signal<NodeResolversMap>({});
  editNodeResolvers = signal<NodeResolversMap>({});
  isSavingEditedRealm = signal<boolean>(false);

  // Computeds
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

  allNodeGroups = computed(() => {
    const nodes = this.systemService.nodes();
    return [
      { id: NO_NODE_ID, label: $localize`All nodes` },
      ...nodes.map((n: NodeInfo) => ({
        label: n.name,
        id: n.uuid
      }))
    ];
  });

  resolverOptions = computed(() => {
    const resolvers = this.resolverService.resolvers();
    return resolvers.map((resolver) => ({
      name: resolver.resolvername,
      type: resolver.type
    }));
  });

  realmRows = computed<RealmRow[]>(() => {
    const realmResource = this.realmService.realmResource.value();
    const realms: Realms | undefined = realmResource?.result?.value as Realms | undefined;
    if (!realms) return [];

    const nodes = this.systemService.nodes();
    const selectedNodeUuid = this.selectedNode();

    return Object.entries(realms as any).flatMap(([realmName, realm]: [string, any]) => {
      const resolvers = realm.resolver ?? [];

      if (selectedNodeUuid !== ALL_NODES_VALUE) {
        const matchesNode = resolvers.some((r: { node: string }) => r.node === selectedNodeUuid);
        if (!matchesNode) return [];
      }

      const groupsMap = new Map<string, ResolverGroup>();

      for (const r of resolvers) {
        const nodeKey = r.node || "__no_node__";

        if (!groupsMap.has(nodeKey)) {
          let nodeLabel: string;
          if (!r.node) {
            nodeLabel = $localize`All nodes`;
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
        .flatMap((g) => g.resolvers.map((rr) => `${rr.name} ${rr.type} ${g.nodeLabel} ${rr.priority ?? ""}`))
        .join(" ");

      return [
        {
          name: realmName,
          isDefault: realm.default,
          resolverGroups,
          resolversText
        } as RealmRow
      ];
    });
  });

  realmsDataSource: WritableSignal<MatTableDataSource<RealmRow>> = linkedSignal({
    source: () => ({
      rows: this.realmRows(),
      sort: this.sort()
    }),
    computation: (src) => {
      const sortedRows = this._clientsideSortRealmData([...(src.rows ?? [])], this.sort());
      const dataSource = new MatTableDataSource(sortedRows);

      dataSource.filterPredicate = (data: RealmRow, filter: string) => {
        const normalizedFilter = filter.trim().toLowerCase();
        if (!normalizedFilter) return true;
        return (
          (data.name ?? "").toLowerCase().includes(normalizedFilter) ||
          (data.resolversText ?? "").toLowerCase().includes(normalizedFilter)
        );
      };

      dataSource.filter = this.filterString().trim().toLowerCase();
      return dataSource;
    }
  });

  constructor() {}

  // --- Filter Handlers ---
  onFilterInput(value: string): void {
    const trimmed = (value ?? "").trim();
    this.filterString.set(trimmed);
    this.realmsDataSource().filter = trimmed.toLowerCase();
  }

  resetFilter(): void {
    this.filterString.set("");
    this.realmsDataSource().filter = "";
    if (this.filterInput?.nativeElement) {
      this.filterInput.nativeElement.value = "";
    }
  }

  // --- Create Handlers ---
  canSubmitNewRealm(): boolean {
    return this.newRealmName().trim().length > 0 && !this.isCreatingRealm();
  }

  resetCreateForm(): void {
    this.newRealmName.set("");
    this.newRealmNodeResolvers.set({});
  }

  getCreateNodeResolvers(nodeId: string): ResolverWithPriority[] {
    return this.newRealmNodeResolvers()[nodeId] ?? [];
  }

  getCreateNodeResolverNames(groupId: string): string[] {
    return this.getCreateNodeResolvers(groupId).map((res) => res.name);
  }

  onNewRealmNodeResolversChange(nodeId: string, values: string[]): void {
    const current = { ...this.newRealmNodeResolvers() };
    const existing = current[nodeId] ?? [];
    const updated: ResolverWithPriority[] = values.map((name) => {
      const found = existing.find((r) => r.name === name);
      return { name, priority: found?.priority ?? null };
    });
    current[nodeId] = updated;
    this.newRealmNodeResolvers.set(current);
  }

  setNewRealmName($event: Event) {
    const input = $event.target as HTMLInputElement;
    this.newRealmName.set(input.value);
  }

  setNewRealmResolverPriority(nodeId: string, resolverName: string, priority: any): void {
    const current = { ...this.newRealmNodeResolvers() };
    const list = current[nodeId] ?? [];
    const entry = list.find((r) => r.name === resolverName);

    const num = Number(priority);
    let value: number | null;

    if (priority === null || priority === undefined || priority === "" || Number.isNaN(num)) {
      value = null;
    } else {
      value = Math.min(999, Math.max(1, num));
    }

    if (entry) {
      entry.priority = value;
    } else {
      list.push({ name: resolverName, priority: value });
    }

    current[nodeId] = [...list];
    this.newRealmNodeResolvers.set(current);
  }

  onCreateRealm(): void {
    if (!this.canSubmitNewRealm()) return;

    this.isCreatingRealm.set(true);
    const realmName = this.newRealmName().trim();
    const nodeResolvers = this.newRealmNodeResolvers();

    const hasGlobalGroup = Object.prototype.hasOwnProperty.call(nodeResolvers, NO_NODE_ID);
    const nodeEntries = Object.entries(nodeResolvers).filter(
      ([nodeId, resolvers]) => nodeId !== NO_NODE_ID && resolvers && resolvers.length > 0
    );

    const requests = [];

    if (hasGlobalGroup) {
      const payload = (nodeResolvers[NO_NODE_ID] ?? []).map((r) => {
        const num = Number(r.priority);
        return r.priority === null || Number.isNaN(num) ? { name: r.name } : { name: r.name, priority: num };
      });
      requests.push(this.realmService.createRealm(realmName, NO_NODE_ID, payload));
    } else if (nodeEntries.length === 0) {
      requests.push(this.realmService.createRealm(realmName, NO_NODE_ID, []));
    }

    nodeEntries.forEach(([nodeId, resolvers]) => {
      const payload = (resolvers ?? []).map((r) => {
        const num = Number(r.priority);
        return r.priority === null || Number.isNaN(num) ? { name: r.name } : { name: r.name, priority: num };
      });
      requests.push(this.realmService.createRealm(realmName, nodeId, payload));
    });

    concat(...requests)
      .pipe(last())
      .subscribe({
        next: () => {
          this._notificationService.openSnackBar($localize`Realm created.`);
          this.resetCreateForm();
          this.realmService.realmResource.reload?.();
        },
        error: (err: HttpErrorResponse) => {
          const message = err.error?.result?.error?.message || err.message;
          this._notificationService.openSnackBar($localize`Failed to create realm. ${message}`);
        }
      })
      .add(() => this.isCreatingRealm.set(false));
  }

  // --- Edit Handlers ---
  canSaveEditedRealm(row: RealmRow): boolean {
    return this.editingRealmName() === row.name && !this.isSavingEditedRealm();
  }

  startEditRealm(row: RealmRow): void {
    if (!row?.name) return;

    const map: NodeResolversMap = {};
    row.resolverGroups.forEach((g) => {
      const key = g.nodeId ?? NO_NODE_ID;
      map[key] = g.resolvers.map((r) => ({
        name: r.name,
        priority: r.priority ?? null
      }));
    });

    const original: NodeResolversMap = {};
    const editable: NodeResolversMap = {};
    Object.entries(map).forEach(([nodeId, list]) => {
      original[nodeId] = list.map((r) => ({ ...r }));
      editable[nodeId] = list.map((r) => ({ ...r }));
    });

    this.editOriginalNodeResolvers.set(original);
    this.editNodeResolvers.set(editable);
    this.editingRealmName.set(row.name);
  }

  cancelEditRealm(): void {
    this.editingRealmName.set(null);
    this.editOriginalNodeResolvers.set({});
    this.editNodeResolvers.set({});
    this.isSavingEditedRealm.set(false);
  }

  getEditNodeResolvers(nodeId: string): ResolverWithPriority[] {
    return this.editNodeResolvers()[nodeId] ?? [];
  }

  getEditNodeResolverNames(nodeId: string): string[] {
    return this.getEditNodeResolvers(nodeId).map((r) => r.name);
  }

  onEditNodeResolversChange(nodeId: string, values: string[]): void {
    const current = this.editNodeResolvers();
    const prevList = current[nodeId] ?? [];

    const updated: ResolverWithPriority[] = values.map((name) => {
      const existing = prevList.find((r) => r.name === name);
      return { name, priority: existing?.priority ?? null };
    });

    this.editNodeResolvers.set({ ...current, [nodeId]: updated });
  }

  setEditResolverPriority(nodeId: string, resolverName: string, priority: any): void {
    const current = this.editNodeResolvers();
    const list = [...(current[nodeId] ?? [])];
    const entry = list.find((r) => r.name === resolverName);

    if (!entry) return;

    const num = Number(priority);
    entry.priority = priority === null || priority === "" || Number.isNaN(num) ? null : Math.min(999, Math.max(1, num));

    this.editNodeResolvers.set({ ...current, [nodeId]: list });
  }

  saveEditedRealm(row: RealmRow): void {
    if (!this.canSaveEditedRealm(row)) return;

    this.isSavingEditedRealm.set(true);
    const realmName = row.name;
    const current = this.editNodeResolvers();

    const hasGlobalGroup = Object.prototype.hasOwnProperty.call(current, NO_NODE_ID);
    const nodeEntries = Object.entries(current).filter(([nodeId]) => nodeId !== NO_NODE_ID);

    if (!hasGlobalGroup && nodeEntries.length === 0) {
      this._notificationService.openSnackBar($localize`No resolvers configured.`);
      this.isSavingEditedRealm.set(false);
      return;
    }

    const requests = [];

    if (hasGlobalGroup) {
      const payload = (current[NO_NODE_ID] ?? []).map((res) => {
        const num = Number(res.priority);
        return res.priority === null || Number.isNaN(num) ? { name: res.name } : { name: res.name, priority: num };
      });
      requests.push(this.realmService.createRealm(realmName, NO_NODE_ID, payload));
    }

    nodeEntries.forEach(([nodeId, list]) => {
      const payload = (list ?? []).map((res) => {
        const num = Number(res.priority);
        return res.priority === null || Number.isNaN(num) ? { name: res.name } : { name: res.name, priority: num };
      });
      requests.push(this.realmService.createRealm(realmName, nodeId, payload));
    });

    concat(...requests)
      .pipe(last())
      .subscribe({
        next: () => {
          this._notificationService.openSnackBar($localize`Realm "${realmName}" updated.`);
          this.cancelEditRealm();
          this.realmService.realmResource.reload?.();
        },
        error: (err: HttpErrorResponse) => {
          const message = err.error?.result?.error?.message || err.message;
          this._notificationService.openSnackBar($localize`Failed to update realm. ${message}`);
        }
      })
      .add(() => this.isSavingEditedRealm.set(false));
  }

  // --- Row Action Handlers ---
  onDeleteRealm(row: RealmRow): void {
    if (!row?.name) return;

    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`Delete Realm`,
          items: [row.name],
          itemType: "realm",
          confirmAction: { label: $localize`Delete`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (!result) return;
          this.realmService.deleteRealm(row.name).subscribe({
            next: () => {
              this._notificationService.openSnackBar($localize`Realm "${row.name}" deleted.`);
              this.realmService.realmResource.reload?.();
            },
            error: (err: HttpErrorResponse) => {
              const message = err.error?.result?.error?.message || err.message;
              this._notificationService.openSnackBar($localize`Failed to delete realm. ${message}`);
            }
          });
        }
      });
  }

  onSetDefaultRealm(row: RealmRow): void {
    if (!row?.name) return;

    this.realmService
      .setDefaultRealm(row.name)
      .pipe(take(1))
      .subscribe({
        next: () => {
          this._notificationService.openSnackBar($localize`Realm "${row.name}" set as default.`);
          this.realmService.realmResource.reload?.();
          this.realmService.defaultRealmResource.reload?.();
        },
        error: (err: HttpErrorResponse) => {
          const message = err.error?.result?.error?.message || err.message;
          this._notificationService.openSnackBar($localize`Failed to set default realm. ${message}`);
        }
      });
  }

  onClickResolver(resolverName: unknown): void {
    const resolver = this.resolverService.resolvers().find((r) => r.resolvername === resolverName);
    if (resolver) {
      this.dialog.open(UserNewResolverComponent, {
        data: { resolver },
        width: "auto",
        height: "auto",
        maxWidth: "100vw",
        maxHeight: "100vh"
      });
    }
  }

  // --- Private Helpers ---
  private _clientsideSortRealmData(data: RealmRow[], s: Sort): RealmRow[] {
    if (!s.direction) return data;
    const dir = s.direction === "desc" ? -1 : 1;
    const key = s.active as keyof RealmRow;

    return data.sort((a: any, b: any) => {
      let va: any;
      let vb: any;
      if (key === "isDefault") {
        va = a.isDefault ? 1 : 0;
        vb = b.isDefault ? 1 : 0;
      } else if (key === "name") {
        va = (a.name ?? "").toString().toLowerCase();
        vb = (b.name ?? "").toString().toLowerCase();
      } else {
        va = (a?.[key] ?? "").toString().toLowerCase();
        vb = (b?.[key] ?? "").toString().toLowerCase();
      }
      if (va < vb) return -1 * dir;
      if (va > vb) return 1 * dir;
      return 0;
    });
  }
}
