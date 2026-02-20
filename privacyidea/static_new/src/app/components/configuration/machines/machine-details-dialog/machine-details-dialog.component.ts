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

import { Component, effect, inject, OnInit, signal, ViewChild } from "@angular/core";
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from "@angular/material/dialog";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatButtonModule } from "@angular/material/button";
import { CommonModule } from "@angular/common";
import { MatIconModule } from "@angular/material/icon";
import { MatTooltipModule } from "@angular/material/tooltip";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { MatPaginator, MatPaginatorModule } from "@angular/material/paginator";
import { FormsModule } from "@angular/forms";
import { MatSelectModule } from "@angular/material/select";
import {
  Machine,
  MachineService,
  MachineServiceInterface,
  TokenApplication,
  TokenApplications
} from "../../../../services/machine/machine.service";
import { ApplicationService, ApplicationServiceInterface } from "../../../../services/application/application.service";
import { DialogService, DialogServiceInterface } from "../../../../services/dialog/dialog.service";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { ROUTE_PATHS } from "../../../../route_paths";

import { CopyButtonComponent } from "../../../shared/copy-button/copy-button.component";

@Component({
  selector: "app-machine-details-dialog",
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatTableModule,
    MatPaginatorModule,
    FormsModule,
    MatSelectModule,
    CopyButtonComponent
  ],
  templateUrl: "./machine-details-dialog.component.html",
  styleUrl: "./machine-details-dialog.component.scss"
})
export class MachineDetailsDialogComponent implements OnInit {
  protected readonly data = inject<Machine>(MAT_DIALOG_DATA);
  private readonly machineService: MachineServiceInterface = inject(MachineService);
  private readonly applicationService: ApplicationServiceInterface = inject(ApplicationService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly dialogRef = inject(MatDialogRef<MachineDetailsDialogComponent>);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  tokenApplications = signal<TokenApplications>([]);
  dataSource = new MatTableDataSource<TokenApplication>([]);
  displayedColumns: string[] = ["serial", "application", "options", "actions"];
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  newTokenSerial = "";
  selectedApplication: "offline" | "ssh" = "offline";
  applicationOptions: string[] = [];
  applicationsDef = this.applicationService.applications;
  // Track edit state and edited options per token id
  editingIds = new Set<number>();
  editedOptions: { [id: number]: Record<string, any> } = {};

  constructor() {
    if (this.dialogRef) {
      this.dialogRef.disableClose = true;
      this.dialogRef.backdropClick().subscribe(() => {
        this.close();
      });
      this.dialogRef.keydownEvents().subscribe(event => {
        if (event.key === "Escape") {
          this.close();
        }
      });
    }

    effect(() => {
      if (!this.contentService.routeUrl().startsWith(ROUTE_PATHS.CONFIGURATION_MACHINES)) {
        this.dialogRef?.close(true);
      }
    });
  }

  ngOnInit(): void {
    this.loadTokenApplications();
    this.applicationOptions = Object.keys(this.applicationsDef()).filter(k => k !== "offline");
  }

  loadTokenApplications(): void {
    this.machineService.getMachineTokens({
      machineid: this.data.id,
      resolver: this.data.resolver_name
    }).subscribe(response => {
      if (response.result?.value) {
        this.tokenApplications.set(response.result?.value ?? [] as TokenApplications);
        this.dataSource.data = response.result?.value;
        this.dataSource.paginator = this.paginator;
      }
    });
  }

  isEditing(tokenId: number): boolean {
    return this.editingIds.has(tokenId);
  }

  startEdit(token: TokenApplication): void {
    this.editingIds.add(token.id);
    this.editedOptions[token.id] = { ...(token.options || {}) };
  }

  cancelEdit(token: TokenApplication): void {
    this.editingIds.delete(token.id);
    delete this.editedOptions[token.id];
  }

  saveOptions(token: TokenApplication): void {
    const edited = this.editedOptions[token.id] || {};
    this.machineService
      .postTokenOption(
        token.hostname,
        String(this.data.id),
        this.data.resolver_name,
        token.serial,
        token.application,
        String(token.id),
        edited
      )
      .subscribe(() => {
        this.loadTokenApplications();
        this.cancelEdit(token);
      });
  }

  detachToken(token: TokenApplication): void {
    this.dialogService.confirm({
      data: {
        title: $localize`Detach Token`,
        serialList: [token.serial],
        type: "token",
        action: "detach"
      }
    }).then(confirmed => {
      if (confirmed) {
        this.machineService.deleteTokenMtid(token.serial, token.application, token.id.toString())
          .subscribe(() => this.loadTokenApplications());
      }
    });
  }

  attachToken(): void {
    if (!this.newTokenSerial || !this.selectedApplication) {
      return;
    }

    this.machineService.postAssignMachineToToken({
      serial: this.newTokenSerial,
      application: this.selectedApplication,
      machineid: this.data.id,
      resolver: this.data.resolver_name
    }).subscribe(() => {
      this.newTokenSerial = "";
      this.selectedApplication = "offline";
      this.loadTokenApplications();
    });
  }

  onTokenClick(serial: string): void {
    this.contentService.tokenSelected(serial);
    this.dialogRef.close();
  }

  onMachineResolverClick(resolverName: string): void {
    this.contentService.machineResolverSelected(resolverName);
    this.dialogRef.close();
  }

  close(): void {
    this.dialogRef.close();
  }
}
