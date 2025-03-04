import { Component, computed, Input, WritableSignal } from '@angular/core';
import { MatIcon } from '@angular/material/icon';
import { MatList, MatListItem } from '@angular/material/list';
import { MatButton } from '@angular/material/button';
import { NgClass } from '@angular/common';
import { tabToggleState } from '../../../../../styles/animations/animations';
import { MatDivider } from '@angular/material/divider';
import { switchMap } from 'rxjs';
import { ContainerService } from '../../../../services/container/container.service';
import { VersionService } from '../../../../services/version/version.service';
import { NotificationService } from '../../../../services/notification/notification.service';
import { ConfirmationDialogComponent } from '../../confirmation-dialog/confirmation-dialog.component';
import { MatDialog } from '@angular/material/dialog';

@Component({
  selector: 'app-container-tab',
  standalone: true,
  imports: [MatIcon, MatList, MatListItem, MatButton, NgClass, MatDivider],
  templateUrl: './container-tab.component.html',
  styleUrl: './container-tab.component.scss',
  animations: [tabToggleState],
})
export class ContainerTabComponent {
  @Input() selectedContent!: WritableSignal<string>;
  @Input() containerSerial!: WritableSignal<string>;
  @Input() states!: WritableSignal<string[]>;
  @Input() refreshContainerDetails!: WritableSignal<boolean>;
  containerIsSelected = computed(() => this.containerSerial() !== '');
  version!: string;

  constructor(
    private containerService: ContainerService,
    private versioningService: VersionService,
    private notificationService: NotificationService,
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
        error: (error) => {
          console.error('Failed to toggle active.', error);
          this.notificationService.openSnackBar('Failed to toggle active.');
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
                error: (error) => {
                  console.error('Failed to delete container.', error);
                  this.notificationService.openSnackBar(
                    'Failed to delete container.',
                  );
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

  openTheDocs() {
    window.open(
      `https://privacyidea.readthedocs.io/en/v${this.version}/webui/index.html#containers`,
      '_blank',
    );
  }

  onClickContainerTab = () => this.onClickOverview();

  onClickOverview() {
    this.selectedContent.set('container_overview');
    this.containerSerial.set('');
  }
}
