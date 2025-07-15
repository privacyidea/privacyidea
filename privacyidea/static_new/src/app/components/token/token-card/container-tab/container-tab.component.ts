import { NgClass } from '@angular/common';
import { Component, computed, Inject } from '@angular/core';
import { MatButton } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatDivider } from '@angular/material/divider';
import { MatIcon } from '@angular/material/icon';
import { MatList, MatListItem } from '@angular/material/list';
import { forkJoin } from 'rxjs';
import { tabToggleState } from '../../../../../styles/animations/animations';
import { ContainerService } from '../../../../services/container/container.service';
import { ContentService } from '../../../../services/content/content.service';
import {
  VersioningService,
  VersioningServiceInterface,
} from '../../../../services/version/version.service';
import { ConfirmationDialogComponent } from '../../../shared/confirmation-dialog/confirmation-dialog.component';

@Component({
  selector: 'app-container-tab',
  standalone: true,
  imports: [MatIcon, MatList, MatListItem, MatButton, NgClass, MatDivider],
  templateUrl: './container-tab.component.html',
  styleUrl: './container-tab.component.scss',
  animations: [tabToggleState],
})
export class ContainerTabComponent {
  containerSelection = this.containerService.containerSelection;
  selectedContent = this.contentService.selectedContent;
  containerSerial = this.containerService.containerSerial;
  selectedContainer = this.containerService.selectedContainer;
  containerIsSelected = computed(() => this.containerSerial() !== '');
  isProgrammaticTabChange = this.contentService.isProgrammaticTabChange;
  states = computed(() => {
    const containerDetail =
      this.containerService.containerDetailResource.value();
    return containerDetail?.result?.value?.containers[0]?.states ?? [];
  });
  version!: string;

  constructor(
    private containerService: ContainerService,
    private contentService: ContentService,
    @Inject(VersioningService)
    private versioningService: VersioningServiceInterface,
    private dialog: MatDialog,
  ) {}

  ngOnInit(): void {
    this.version = this.versioningService.getVersion();
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
          title: 'Delete Container',
          type: 'container',
          action: 'delete',
          numberOfTokens: 1,
        },
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.containerService
              .deleteContainer(this.containerSerial())
              .subscribe({
                next: () => {
                  this.selectedContent.set('container_overview');
                  this.containerSerial.set('');
                },
              });
          }
        },
      });
  }

  deleteSelectedContainer(): void {
    const selectedContainers = this.containerSelection();
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serial_list: selectedContainers.map((container) => container.serial),
          title: 'Delete All Containers',
          type: 'container',
          action: 'delete',
          numberOfContainers: selectedContainers.length,
        },
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            forkJoin(
              selectedContainers.map((container) =>
                this.containerService.deleteContainer(container.serial),
              ),
            ).subscribe({
              next: () => {
                this.containerSelection.set([]);
                this.containerService.containerResource.reload();
              },
              error: (err) => {
                console.error('Error deleting containers:', err);
              },
            });
          }
        },
      });
  }

  lostContainer() {
    // TODO: Missing API endpoint
  }

  damagedContainer() {
    // TODO: Missing API endpoint
  }

  onClickContainerTab = () => this.onClickContainerOverview();

  onClickContainerOverview() {
    this.selectedContent.set('container_overview');
  }

  enrollTokenInContainer() {
    this.selectedContainer.set(this.containerSerial());
    this.isProgrammaticTabChange.set(true);
    this.selectedContent.set('token_enrollment');
  }

  onClickCreateContainer() {
    this.selectedContent.set('container_create');
  }
}
