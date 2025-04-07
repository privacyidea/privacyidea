import { Component, computed, Input, WritableSignal } from '@angular/core';
import { MatIcon } from '@angular/material/icon';
import { MatList, MatListItem } from '@angular/material/list';
import { MatButton } from '@angular/material/button';
import { NgClass } from '@angular/common';
import { tabToggleState } from '../../../../../styles/animations/animations';
import { MatDivider } from '@angular/material/divider';
import { forkJoin, switchMap } from 'rxjs';
import { ContainerService } from '../../../../services/container/container.service';
import { VersionService } from '../../../../services/version/version.service';
import { ConfirmationDialogComponent } from '../../../shared/confirmation-dialog/confirmation-dialog.component';
import { MatDialog } from '@angular/material/dialog';
import { TokenSelectedContent } from '../../token.component';

@Component({
  selector: 'app-container-tab',
  standalone: true,
  imports: [MatIcon, MatList, MatListItem, MatButton, NgClass, MatDivider],
  templateUrl: './container-tab.component.html',
  styleUrl: './container-tab.component.scss',
  animations: [tabToggleState],
})
export class ContainerTabComponent {
  @Input() selectedContent!: WritableSignal<TokenSelectedContent>;
  @Input() containerSerial!: WritableSignal<string>;
  @Input() states!: WritableSignal<string[]>;
  @Input() refreshContainerDetails!: WritableSignal<boolean>;
  @Input() refreshContainerOverview!: WritableSignal<boolean>;
  @Input() isProgrammaticChange!: WritableSignal<boolean>;
  @Input() containerSelection!: WritableSignal<any[]>;
  containerIsSelected = computed(() => this.containerSerial() !== '');
  version!: string;

  constructor(
    private containerService: ContainerService,
    protected versioningService: VersionService,
    private dialog: MatDialog,
  ) {}

  ngOnInit(): void {
    this.version = this.versioningService.getVersion();
  }

  toggleActive(): void {
    this.containerService
      .toggleActive(this.containerSerial(), this.states())
      .pipe(
        switchMap(() =>
          this.containerService.getContainerDetails(this.containerSerial()),
        ),
      )
      .subscribe({
        next: () => {
          this.refreshContainerDetails.set(true);
        },
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
                this.refreshContainerOverview.set(true);
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
    this.containerSerial.set(this.containerSerial());
  }

  onClickCreateContainer() {
    this.selectedContent.set('container_create');
    this.containerSerial.set('');
  }
}
