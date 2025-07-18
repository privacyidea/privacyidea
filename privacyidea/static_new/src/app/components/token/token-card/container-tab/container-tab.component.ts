import { Component, computed, Inject } from '@angular/core';
import { NgClass } from '@angular/common';
import { Router } from '@angular/router';
import { MatIcon } from '@angular/material/icon';
import { MatList, MatListItem } from '@angular/material/list';
import { MatButton } from '@angular/material/button';
import { MatDivider } from '@angular/material/divider';
import { MatDialog } from '@angular/material/dialog';
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
  states = computed(() => {
    const detail = this.containerService.containerDetailResource.value();
    return detail?.result?.value?.containers[0]?.states ?? [];
  });
  version!: string;

  constructor(
    private router: Router,
    private containerService: ContainerService,
    private contentService: ContentService,
    @Inject(VersioningService)
    protected versioningService: VersioningServiceInterface,
    private dialog: MatDialog,
  ) {}

  ngOnInit(): void {
    this.version = this.versioningService.getVersion();
  }

  go(path: string) {
    this.contentService.isProgrammaticTabChange.set(true);
    this.router.navigateByUrl(path);
  }

  onClickContainerOverview() {
    this.go('/tokens/containers');
  }

  enrollTokenInContainer() {
    this.selectedContainer.set(this.containerSerial());
    this.go('/tokens/enroll');
  }

  toggleActive(): void {
    this.containerService
      .toggleActive(this.containerSerial(), this.states())
      .subscribe(() => this.containerService.containerDetailResource.reload());
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
      .subscribe((ok) => {
        if (ok) {
          this.containerService
            .deleteContainer(this.containerSerial())
            .subscribe(() => this.go('/tokens/containers'));
        }
      });
  }

  deleteSelectedContainer(): void {
    const cs = this.containerSelection();
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serial_list: cs.map((c) => c.serial),
          title: 'Delete All Containers',
          type: 'container',
          action: 'delete',
          numberOfContainers: cs.length,
        },
      })
      .afterClosed()
      .subscribe((ok) => {
        if (ok) {
          forkJoin(
            cs.map((c) => this.containerService.deleteContainer(c.serial)),
          ).subscribe(() => {
            this.containerSelection.set([]);
            this.containerService.containerResource.reload();
          });
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
