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
import {
  Component,
  ViewChild,
  WritableSignal,
  computed,
  inject,
  linkedSignal,
  signal
} from "@angular/core";
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
import { I18nSelectPipe, NgClass } from "@angular/common";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";

import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../services/table-utils/table-utils.service";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { RealmService, RealmServiceInterface, Realms } from "../../../services/realm/realm.service";
import { SystemService, SystemServiceInterface, NodeInfo } from "../../../services/system/system.service";

export interface RealmRow {
  name: string;
  isDefault: boolean;
  resolvers: string;
  nodes: string;
}

// Optional: tweak columns as needed
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
    I18nSelectPipe
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

  // --- Filter state ----------------------------------------------------------
  /** Node selection: ALL_NODES_VALUE or a specific node.uuid */
  selectedNode = signal<string>(ALL_NODES_VALUE);

  /** Simple text filter for the realms table */
  filterString = signal<string>("");

  // Node options for the <mat-select>
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

  // Total length (after node filter, before text filter)
  totalLength: WritableSignal<number> = computed(() => {
    const rows = this.realmRows();
    return rows.length;
  }) as WritableSignal<number>;

  // --- Data preparation ------------------------------------------------------

  /** Full list of RealmRow, filtered by selected node only */
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

      // Node filter logic (in-memory, as requested)
      if (selectedNodeUuid !== ALL_NODES_VALUE) {
        const matchesNode = resolvers.some((r: { node: string; }) => r.node === selectedNodeUuid);
        if (!matchesNode) {
          return [];
        }
      }

      const resolverNames = resolvers.map((r: { name: any; }) => r.name).join(", ");

      // Show human-readable node names if we know them
      const nodeNames = Array.from(
        new Set(
          resolvers
            .map((r: { node: string; }) => {
              if (!r.node) {
                return "";
              }
              const node = nodes.find((n) => n.uuid === r.node || n.name === r.node);
              return node?.name ?? r.node;
            })
            .filter(Boolean)
        )
      ).join(", ");

      return [
        {
          name: realmName,
          isDefault: realm.default,
          resolvers: resolverNames,
          nodes: nodeNames
        } as RealmRow
      ];
    });
  });

  // --- Data source for MatTable ---------------------------------------------

  /** Data for the table, with MatTableDataSource to support text filter & sort */
  realmsDataSource: WritableSignal<MatTableDataSource<RealmRow>> = linkedSignal({
    source: this.realmRows,
    computation: (rows, previous) => {
      const dataSource = new MatTableDataSource(rows ?? []);
      dataSource.paginator = this.paginator;
      dataSource.sort = this.sort;

      // apply text filter from filterString
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

  // --- Handlers --------------------------------------------------------------

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
