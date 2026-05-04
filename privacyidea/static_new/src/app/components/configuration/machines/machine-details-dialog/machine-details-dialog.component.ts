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
import { lastValueFrom } from "rxjs";
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
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import {
  Machine,
  MachineService,
  MachineServiceInterface,
  TokenApplication,
  TokenApplications
} from "../../../../services/machine/machine.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { ApplicationService, ApplicationServiceInterface } from "../../../../services/application/application.service";
import { DialogService, DialogServiceInterface } from "../../../../services/dialog/dialog.service";
import { SimpleConfirmationDialogComponent } from "../../../shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { ROUTE_PATHS } from "../../../../route_paths";
import { CopyButtonComponent } from "../../../shared/copy-button/copy-button.component";
import { ActivatedRoute, Router } from "@angular/router";

@Component({
  selector: "app-machine-details-dialog",
  standalone: true,
  imports: [
    CommonModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatTableModule,
    MatPaginatorModule,
    FormsModule,
    MatSelectModule,
    MatAutocompleteModule,
    CopyButtonComponent
  ],
  templateUrl: "./machine-details-dialog.component.html",
  styleUrl: "./machine-details-dialog.component.scss"
})
export class MachineDetailsDialogComponent implements OnInit {
  private readonly machineService: MachineServiceInterface = inject(MachineService);
  private readonly applicationService: ApplicationServiceInterface = inject(ApplicationService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly router: Router = inject(Router);
  private readonly route: ActivatedRoute = inject(ActivatedRoute);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;

  data = signal<Machine | undefined>(history.state?.machine as Machine | undefined);
  private readonly routeMachineId: string | null;
  private readonly routeResolver: string | null;
  tokenApplications = signal<TokenApplications>([]);
  dataSource = new MatTableDataSource<TokenApplication>([]);
  displayedColumns: string[] = ["serial", "application", "options", "actions"];
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  newTokenSerial = "";
  selectedApplication: "offline" | "ssh" = "offline";
  applicationOptions: string[] = [];
  applicationsDef = this.applicationService.applications;
  editingIds = new Set<number>();
  editedOptions: { [id: number]: Record<string, any> } = {};

  constructor() {
    this.routeMachineId = this.route.snapshot.paramMap.get("id");
    this.routeResolver = this.route.snapshot.queryParamMap.get("resolver");

    effect(() => {
      const machines = this.machineService.machines();
      if (!this.data() && this.routeMachineId && machines?.length) {
        const found = machines.find(m => String(m.id) === this.routeMachineId
          && (!this.routeResolver || m.resolver_name === this.routeResolver));
        if (found) {
          this.data.set(found);
          this.loadTokenApplications();
        }
      }
    });
  }

  ngOnInit(): void {
    this.applicationOptions = Object.keys(this.applicationsDef()).filter(k => k !== "offline");
    if (this.data()) {
      this.loadTokenApplications();
    }
    // If data() is still undefined, the effect() will handle it once machines signal resolves.
  }

  onTokenSerialInput(value: string): void {
    this.tokenService.selectedToken.set(value);
  }

  loadTokenApplications(): void {
    const machine = this.data();
    if (!machine) return;
    this.machineService.getMachineTokens({
      machineid: machine.id,
      resolver: machine.resolver_name
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
    const machine = this.data();
    if (!machine) return;
    const edited = this.editedOptions[token.id] || {};
    this.machineService
      .postTokenOption(
        token.hostname,
        String(machine.id),
        machine.resolver_name,
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
    lastValueFrom(this.dialogService.openDialog({
      component: SimpleConfirmationDialogComponent,
      data: {
        title: $localize`Detach Token`,
        items: [token.serial],
        itemType: "token",
        confirmAction: { label: $localize`Detach`, value: true, type: "destruct" }
      }
    }).afterClosed()).then(confirmed => {
      if (confirmed) {
        this.machineService.deleteTokenById(token.serial, token.application, token.id.toString())
          .subscribe(() => this.loadTokenApplications());
      }
    });
  }

  attachToken(): void {
    const machine = this.data();
    if (!this.newTokenSerial || !this.selectedApplication || !machine) {
      return;
    }

    this.machineService.postAssignMachineToToken({
      serial: this.newTokenSerial,
      application: this.selectedApplication,
      machineid: machine.id,
      resolver: machine.resolver_name
    }).subscribe(() => {
      this.newTokenSerial = "";
      this.selectedApplication = "offline";
      this.loadTokenApplications();
    });
  }

  onTokenClick(serial: string): void {
    this.contentService.tokenSelected(serial);
  }

  onMachineResolverClick(resolverName: string): void {
    this.contentService.machineResolverSelected(resolverName);
  }
}
