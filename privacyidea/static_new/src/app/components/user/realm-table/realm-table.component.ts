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
import { Component, computed, inject, linkedSignal, signal, ViewChild, WritableSignal } from "@angular/core";
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
import { MatPaginator } from "@angular/material/paginator";
import { MatSort, MatSortModule } from "@angular/material/sort";
import { FormsModule } from "@angular/forms";
import { NgClass } from "@angular/common";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";

import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../services/table-utils/table-utils.service";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { RealmService, RealmServiceInterface, ResolverGroup } from "../../../services/realm/realm.service";
import { NodeInfo, SystemService, SystemServiceInterface } from "../../../services/system/system.service";
import { MatIcon } from "@angular/material/icon";

export interface RealmRow {
  name: string;
  isDefault: boolean;
  resolvers: string;
  nodes: string;
}

const columnKeysMap = [
  { key: "name", label: "Realm" },
  { key: "isDefault", label: "Default" },
  { key: "resolvers", label: "Resolvers" },
  { key: "nodes", label: "Nodes" }
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
    MatIcon
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

  realmRows = computed<RealmRow[]>(() => {
    const realmResource = this.realmService.realmResource.value();
    const realms = realmResource?.result?.value;
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
            nodeLabel = "All nodes";
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

      const nodeNames = Array.from(
        new Set(
          resolverGroups
            .map((g) => g.nodeLabel)
            .filter((label) => !!label && label !== "All nodes")
        )
      ).join(", ");

      const resolversText = resolverGroups
        .flatMap((g) =>
          g.resolvers.map(
            (r) => `${r.name} ${r.type} ${g.nodeLabel} ${r.priority ?? ""}`
          )
        )
        .join(" ");

      return [
        {
          name: realmName,
          isDefault: realm.default,
          resolverGroups,
          nodes: nodeNames,
          resolversText
        } as unknown as RealmRow
      ];
    });
  });

  totalLength: WritableSignal<number> = computed(() => {
    const rows = this.realmRows();
    return rows.length;
  }) as WritableSignal<number>;

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
          data.resolvers.toLowerCase().includes(normalizedFilter) ||
          data.nodes.toLowerCase().includes(normalizedFilter)
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
}
