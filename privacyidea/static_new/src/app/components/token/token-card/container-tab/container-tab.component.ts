import { Component, computed } from '@angular/core';
import { MatIcon } from '@angular/material/icon';
import { MatList, MatListItem } from '@angular/material/list';
import { MatButton } from '@angular/material/button';
import { NgClass } from '@angular/common';
import { MatDivider } from '@angular/material/divider';
import { forkJoin } from 'rxjs';
import { ContainerService } from '../../../../services/container/container.service';
import { VersionService } from '../../../../services/version/version.service';
import { ConfirmationDialogComponent } from '../../../shared/confirmation-dialog/confirmation-dialog.component';
import { MatDialog } from '@angular/material/dialog';
import { tabToggleState } from '../../../../../styles/animations/animations';
import { TokenService } from '../../../../services/token/token.service';

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
  selectedContent = this.tokenService.selectedContent;
  containerSerial = this.tokenService.containerSerial;
  containerIsSelected = computed(() => this.containerSerial() !== '');
  isProgrammaticChange = this.tokenService.isProgrammaticTabChange;
  states = computed(() => {
    const containerDetail =
      this.containerService.containerDetailResource.value();
    return containerDetail?.result?.value?.containers[0]?.states ?? [];
  });
  version!: string;

  constructor(
    private containerService: ContainerService,
    private tokenService: TokenService,
    protected versioningService: VersionService,
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
          serial_list: selectedContainers.map(
            (container: any) => container.serial,
          ),
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
              selectedContainers.map((container: any) =>
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

  onClickContainerTab = () => this.onClickOverview();

  onClickOverview() {
    this.selectedContent.set('container_overview');
    this.containerSerial.set('');
  }

  enrollTokenInContainer() {
    this.selectedContent.set('token_enrollment');
    this.isProgrammaticChange.set(true);
    this.containerService.selectedContainer.set(this.containerSerial());
  }

  onClickCreateContainer() {
    this.selectedContent.set('container_create');
    this.containerSerial.set('');
  }
}
