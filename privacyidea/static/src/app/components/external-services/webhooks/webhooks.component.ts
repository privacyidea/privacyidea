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

import { Component, computed, ElementRef, inject, signal, ViewChild, viewChild, WritableSignal } from "@angular/core";
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
import { TableStateComponent } from "@components/shared/table-state/table-state.component";
import { TableState } from "@core/models/table_state/table-state";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { renderedRows, RowSelector } from "@services/table-utils/row-selector";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { Webhook, WebhookService, WebhookServiceInterface } from "@services/webhook/webhook.service";

@Component({
  selector: "app-webhooks",
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
    CopyableComponent,
    TableStateComponent
  ],
  templateUrl: "./webhooks.component.html",
  styleUrl: "./webhooks.component.scss"
})
export class WebhooksComponent {
  selector = new RowSelector<Webhook>({
    keyGetter: (webhook) => webhook.identifier,
    visibleRows: renderedRows(this.webhookDataSource)
  });
  protected readonly webhookService: WebhookServiceInterface = inject(WebhookService);
  totalLength: WritableSignal<number> = computed(() => this.webhookService.webhooks().length) as WritableSignal<number>;
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  readonly tableState = new TableState({
    resource: this.webhookService.webhookResource,
    count: () => this.webhookService.webhooks().length,
    allowed: () => this.authService.actionAllowed("webhook_read"),
    resetFilter: () => this.resetFilter()
  });
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);

  filterString = signal<string>("");
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  protected readonly ROUTE_PATHS = ROUTE_PATHS;

  readonly paginator = viewChild(MatPaginator);
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild("filterHTMLInputElement", { static: false }) filterInput!: ElementRef<HTMLInputElement>;

  displayedColumns: string[] = ["select", "identifier", "url", "http_method", "auth_type", "description"];

  webhookDataSource = computed(() => {
    const webhooks = this.webhookService.webhooks();
    const dataSource = new MatTableDataSource(webhooks);
    dataSource.paginator = this.paginator() ?? null;
    dataSource.sort = this.sort;
    return dataSource;
  });
  private readonly router = inject(Router);

  onCreateNewWebhook(): void {
    this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_WEBHOOKS_NEW);
  }

  onEditWebhook(webhook: Webhook): void {
    this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_WEBHOOKS_DETAILS + webhook.identifier);
  }

  deleteSelected(): void {
    const selected = this.selector.selectedRows();
    if (selected.length === 0) {
      return;
    }
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`:@@webhook.deleteWebhooks:Delete Webhooks`,
          items: selected.map((row) => row.identifier),
          itemType: "webhook",
          confirmAction: { label: $localize`:@@common.delete:Delete`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result) {
          selected.forEach((row) => void this.webhookService.deleteWebhook(row.identifier).catch(() => undefined));
          this.selector.deselectAllRows();
        }
      });
  }

  onFilterInput(value: string): void {
    const trimmed = (value ?? "").trim();
    this.filterString.set(trimmed);

    const ds = this.webhookDataSource();
    ds.filter = trimmed.toLowerCase();
  }

  resetFilter(): void {
    this.filterString.set("");
    const ds = this.webhookDataSource();
    ds.filter = "";
    const inputEl = this.filterInput?.nativeElement as HTMLInputElement | undefined;
    if (inputEl) {
      inputEl.value = "";
    }
  }
}
