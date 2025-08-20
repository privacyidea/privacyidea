import { MatIcon } from "@angular/material/icon";
import { MatList, MatListItem } from "@angular/material/list";
import { MatButton } from "@angular/material/button";
import { MatDivider } from "@angular/material/divider";
import { MatDialog } from "@angular/material/dialog";
import { forkJoin } from "rxjs";
import { tabToggleState } from "../../../../../styles/animations/animations";
import { ContainerService, ContainerServiceInterface } from "../../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { VersioningService, VersioningServiceInterface } from "../../../../services/version/version.service";
import { NgClass } from "@angular/common";
import { Component, computed, inject } from "@angular/core";
import { ConfirmationDialogComponent } from "../../../shared/confirmation-dialog/confirmation-dialog.component";
import { Router, RouterLink } from "@angular/router";
import { ROUTE_PATHS } from "../../../../app.routes";

@Component({
  selector: "app-container-tab",
  standalone: true,
  imports: [
    MatIcon,
    MatList,
    MatListItem,
    MatButton,
    NgClass,
    MatDivider,
    RouterLink
  ],
  templateUrl: "./container-tab.component.html",
  styleUrl: "./container-tab.component.scss",
  animations: [tabToggleState]
})
export class ContainerTabComponent {
  private readonly dialog: MatDialog = inject(MatDialog);
  private readonly containerService: ContainerServiceInterface =
    inject(ContainerService);
  protected readonly contentService: ContentServiceInterface =
    inject(ContentService);
  protected readonly versioningService: VersioningServiceInterface =
    inject(VersioningService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  private router = inject(Router);
  containerSelection = this.containerService.containerSelection;
  containerSerial = this.containerService.containerSerial;
  selectedContainer = this.containerService.selectedContainer;
  containerIsSelected = computed(() => this.containerSerial() !== "");
  states = computed(() => {
    const containerDetail =
      this.containerService.containerDetailResource.value();
    return containerDetail?.result?.value?.containers[0]?.states ?? [];
  });
  version!: string;

  ngOnInit(): void {
    this.version = this.versioningService.getVersion();
  }

  onClickContainerOverview() {
    this.router.navigateByUrl(ROUTE_PATHS.TOKENS_CONTAINERS);
  }

  enrollTokenInContainer() {
    this.contentService.isProgrammaticTabChange.set(true);
    this.selectedContainer.set(this.containerSerial());
    this.router.navigateByUrl(ROUTE_PATHS.TOKENS_ENROLLMENT);
  }

  toggleActive(): void {
    this.containerService
      .toggleActive(this.containerSerial(), this.states())
      .subscribe(() => {
        this.containerService.containerDetailResource.reload();
      });
  }

  deleteContainer() {
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serial_list: [this.containerSerial()],
          title: "Delete Container",
          type: "container",
          action: "delete",
          numberOfTokens: 1
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result) {
          this.containerService
            .deleteContainer(this.containerSerial())
            .subscribe(() => {
              const prev = this.contentService.previousUrl();

              if (prev.startsWith(ROUTE_PATHS.TOKENS_DETAILS)) {
                this.contentService.isProgrammaticTabChange.set(true);
                this.router.navigateByUrl(prev);
              } else {
                this.router.navigateByUrl(ROUTE_PATHS.TOKENS_CONTAINERS);
              }
            });
        }
      });
  }

  deleteSelectedContainer(): void {
    const selectedContainers = this.containerSelection();
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serial_list: selectedContainers.map((container) => container.serial),
          title: "Delete All Containers",
          type: "container",
          action: "delete",
          numberOfContainers: selectedContainers.length
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            forkJoin(
              selectedContainers.map((container) =>
                this.containerService.deleteContainer(container.serial)
              )
            ).subscribe({
              next: () => {
                this.containerSelection.set([]);
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

  lostContainer() {
    // TODO: Missing API endpoint
  }

  damagedContainer() {
    // TODO: Missing API endpoint
  }
}
