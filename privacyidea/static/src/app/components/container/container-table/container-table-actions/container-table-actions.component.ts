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
import { Component, computed, DOCUMENT, inject, input, output, signal, viewChild } from "@angular/core";

import { MatMenuTrigger } from "@angular/material/menu";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { AuthService } from "@services/auth/auth.service";
import { ContainerService, ContainerServiceInterface } from "@services/container/container.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { DocumentationService } from "@services/documentation/documentation.service";
import { NotificationService } from "@services/notification/notification.service";
import { ContainerTemplateComparisonRow } from "@services/container/container.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { VersioningService, VersioningServiceInterface } from "@services/version/version.service";
import { forkJoin } from "rxjs";
import { TableAction, TableActionsComponent } from "../../../shared/table-actions/table-actions.component";
import { TableActionsHost } from "../../../shared/table-actions/table-actions-host";

@Component({
  selector: "app-container-table-actions",
  imports: [TableActionsComponent],
  templateUrl: "./container-table-actions.component.html"
})
export class ContainerTableActionsComponent extends TableActionsHost {
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  private readonly document: Document = inject(DOCUMENT);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  protected readonly documentationService = inject(DocumentationService);
  protected readonly authService = inject(AuthService);
  protected readonly notificationService = inject(NotificationService);
  readonly advancedApiFilterKeys = this.containerService.advancedApiFilterKeys;
  readonly advancedFilterTrigger = viewChild<MatMenuTrigger>("advancedFilterTrigger");
  private readonly router = inject(Router);
  containerSelection = this.containerService.containerSelection;
  selectedContainer = this.containerService.selectedContainerSerial;
  readonly comparisonActive = input(false);
  readonly comparisonLoaded = output<ContainerTemplateComparisonRow[]>();
  readonly comparisonHidden = output<void>();
  protected readonly comparingContainers = signal(false);

  protected readonly actions = computed<TableAction[]>(() => [
    {
      id: "create",
      label: $localize`:@@common.createContainer:Create Container`,
      tone: "primary",
      width: "m",
      icon: "folder",
      iconClass: "icon-badge-pad-3",
      badge: true,
      pinned: true,
      visible: this.authService.actionAllowed("container_create"),
      run: () => this.router.navigate([ROUTE_PATHS.CONTAINERS_CREATE])
    },
    {
      id: "delete",
      label: $localize`:@@common.delete:Delete`,
      tone: "delete-secondary",
      width: "m",
      icon: "delete_sweep",
      visible: this.authService.actionAllowed("container_delete"),
      disabled: !this.containerSelection.hasSelection(),
      run: () => this.deleteSelectedContainer()
    },
    {
      id: "compare",
      label: this.comparisonActive()
        ? $localize`:@@container.hideComparison:Hide comparison`
        : $localize`:@@container.compareWithTemplates:Compare with templates`,
      tone: "secondary",
      width: "l",
      icon: "compare_arrows",
      visible: this.authService.actionAllowed("container_template_list"),
      disabled: this.comparingContainers(),
      run: () => void this.toggleComparison()
    }
  ]);

  deleteSelectedContainer(): void {
    const selectedContainers = this.containerSelection.selectedRows();
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`:@@container.deleteAllContainers:Delete All Containers`,
          items: selectedContainers.map((container) => container.serial),
          itemType: "container",
          confirmAction: { label: $localize`:@@common.delete:Delete`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            forkJoin(
              selectedContainers.map((container) => this.containerService.deleteContainer(container.serial))
            ).subscribe({
              next: () => {
                this.notificationService.success(
                  $localize`:@@container.successfullyDeleted:Successfully deleted ${selectedContainers.length}:COUNT: containers.`
                );
                this.containerSelection.deselectAllRows();
                this.containerService.containerResource.reload();
              },
              error: (err) => {
                console.error("Error deleting containers:", err);
              }
            });
          }
        }
      });
  }

  async toggleComparison(): Promise<void> {
    if (this.comparisonActive()) {
      this.comparisonHidden.emit();
      return;
    }
    await this.compareDisplayedContainers();
  }

  private async compareDisplayedContainers(): Promise<void> {
    const displayedContainers = this.containerService.containerResource.value()?.result?.value?.containers ?? [];
    if (displayedContainers.length === 0 || this.comparingContainers()) {
      return;
    }

    this.comparingContainers.set(true);
    try {
      const comparisons: ContainerTemplateComparisonRow[] =
        await this.containerService.compareContainersWithTemplates(displayedContainers);
      this.comparisonLoaded.emit(comparisons);
    } catch (error) {
      console.error("Failed to compare containers with their templates:", error);
      const message =
        error instanceof Error && error.message
          ? error.message
          : $localize`:@@container.unknownComparisonError:An unknown error occurred.`;
      this.notificationService.error(
        $localize`:@@container.failedToCompareSelected:Failed to compare selected containers. ${message}:MESSAGE:`
      );
    } finally {
      this.comparingContainers.set(false);
    }
  }

  getFilterIconName(keyword: string): string {
    if (keyword === "assigned") {
      const value = this.containerService.activeFilter().booleanValueOfKey(keyword);
      if (value === undefined) {
        return "filter_alt";
      }
      return value ? "screen_rotation_alt" : "filter_alt_off";
    }
    const isSelected = this.containerService.activeFilter().hasKey(keyword);
    return isSelected ? "filter_alt_off" : "filter_alt";
  }

  onAdvancedFilterClick(filterKeyword: string): void {
    this.toggleFilter(filterKeyword);
    if (filterKeyword === "assigned") {
      setTimeout(() => this.advancedFilterTrigger()?.openMenu());
      return;
    }
    setTimeout(() => {
      const elementById = this.document.getElementById("container-filter-input") as HTMLInputElement | null;
      elementById?.focus();
    });
  }

  private toggleFilter(filterKeyword: string): void {
    this.containerService.updateFilter((current) =>
      filterKeyword === "assigned"
        ? this.tableUtilsService.toggleBooleanInFilter({
            keyword: filterKeyword,
            currentValue: current
          })
        : this.tableUtilsService.toggleKeywordInFilter({
            keyword: filterKeyword,
            currentValue: current
          })
    );
  }
}
