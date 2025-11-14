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
import { Component, effect, inject, linkedSignal, signal, ViewChild, WritableSignal } from "@angular/core";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import {
  MatCell,
  MatCellDef,
  MatColumnDef,
  MatHeaderCell,
  MatHeaderCellDef,
  MatHeaderRow,
  MatHeaderRowDef,
  MatRow,
  MatRowDef,
  MatTable,
  MatTableDataSource,
  MatTableModule
} from "@angular/material/table";
import {
  ClientData,
  ClientsDict,
  ClientsService,
  ClientsServiceInterface
} from "../../../services/clients/clients.service";
import { MatSort, MatSortHeader, MatSortModule } from "@angular/material/sort";
import { NgClass } from "@angular/common";
import { CommonModule } from "@angular/common";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { CopyButtonComponent } from "../../shared/copy-button/copy-button.component";
import { AuthService } from "../../../services/auth/auth.service";
import { AuditService } from "../../../services/audit/audit.service";
import { FilterValue } from "../../../core/models/filter_value";
import { ROUTE_PATHS } from "../../../route_paths";
import { RouterLink } from "@angular/router";
import { MatIconButton } from "@angular/material/button";
import { MatTooltip } from "@angular/material/tooltip";
import { MatIcon } from "@angular/material/icon";

const columnKeysMap = [
  { key: "application", label: "Application" },
  { key: "hostname", label: "Hostname" },
  { key: "ip", label: "IP Address" },
  { key: "lastseen", label: "Last Seen" }
];

export interface ClientTableRow {
  application: string;
  clientData: ClientData[];
}

// Helper interface for flattened rows
interface FlattenedClientRow {
  application: string;
  hostname?: string;
  ip?: string;
  lastseen?: Date; // Change to Date
  isFirst: boolean;
  rowspan: number;
}

@Component({
  selector: "app-clients",
  templateUrl: "./clients.component.html",
  styleUrls: ["./clients.component.scss"],
  imports: [
    ScrollToTopDirective,
    MatTable,
    MatTableModule,
    MatColumnDef,
    MatCell,
    MatCellDef,
    MatHeaderCell,
    MatHeaderCellDef,
    MatHeaderRow,
    MatHeaderRowDef,
    MatRow,
    MatRowDef,
    MatSort,
    MatSortHeader,
    MatSortModule,
    NgClass,
    CommonModule,
    MatFormField,
    MatInput,
    MatLabel,
    MatFormField,
    CopyButtonComponent,
    RouterLink,
    MatIconButton,
    MatTooltip,
    MatIcon
  ]
})
export class ClientsComponent {
  clientService: ClientsServiceInterface = inject(ClientsService);
  authService = inject(AuthService);
  auditService = inject(AuditService);

  readonly columnKeysMap = columnKeysMap;
  readonly columnKeys = ["application", "hostname", "ip", "lastseen"];

  activeSortColumn = signal<string | null>(null);

  onSortChange(event: { active: string }) {
    this.activeSortColumn.set(event.active || null);
  }

  @ViewChild(MatSort) sort!: MatSort;

  constructor() {
    effect(() => {
      this.clientDataSource().sort = this.sort;
    });
  }

  // Flattens the grouped client data for the material table, from ClientsDict
  flattenedClientRowsFromDict = (dict: ClientsDict): FlattenedClientRow[] => {
    const rows: FlattenedClientRow[] = [];
    for (const application of Object.keys(dict)) {
      const clientDataArr = dict[application];
      const len = clientDataArr.length;
      clientDataArr.forEach((client, idx) => {
        rows.push({
          application,
          hostname: client.hostname,
          ip: client.ip,
          lastseen: client.lastseen ? new Date(client.lastseen) : undefined, // Convert to Date
          isFirst: idx === 0,
          rowspan: idx === 0 ? len : 0
        });
      });
    }
    return rows;
  };

  clientResource = this.clientService.clientsResource;
  clientDataSource: WritableSignal<MatTableDataSource<FlattenedClientRow>> = linkedSignal({
    source: this.clientResource.value,
    computation: (clientResource, previous) => {
      if (clientResource) {
        const clientData = clientResource.result?.value || {} as ClientsDict;
        const dataSource = new MatTableDataSource(this.flattenedClientRowsFromDict(clientData));
        // Custom sorting for lastseen
        dataSource.sortingDataAccessor = (item, property) => {
          if (property === 'lastseen') {
            return item.lastseen ? item.lastseen.getTime() : 0;
          }
          return (item as any)[property];
        };
        return dataSource;
      }
      return previous?.value ?? new MatTableDataSource([] as FlattenedClientRow[]);
    }
  });

  filterValue: string = "";

  handleFilterInput($event: Event): void {
    this.filterValue = ($event.target as HTMLInputElement).value.trim();
    this.clientDataSource().filter = this.filterValue.toLowerCase();
  }

   protected showIpInAuditLog(ip: string): void {
    this.auditService.auditFilter.set(new FilterValue({ value: `client: ${ip}` }));
  }

  protected readonly ROUTE_PATHS = ROUTE_PATHS;
}
