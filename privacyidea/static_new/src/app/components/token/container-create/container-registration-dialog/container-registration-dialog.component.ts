import { Component, inject, WritableSignal } from '@angular/core';
import {
  MAT_DIALOG_DATA,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';
import { PiResponse } from '../../../../app.component';
import {
  ContainerRegisterData,
  ContainerService,
  ContainerServiceInterface,
} from '../../../../services/container/container.service';
import { LostTokenComponent } from '../../token-card/token-tab/lost-token/lost-token.component';

@Component({
  selector: 'app-container-registration-dialog',
  imports: [MatDialogContent, MatDialogTitle],
  templateUrl: './container-registration-dialog.component.html',
  styleUrl: './container-registration-dialog.component.scss',
})
export class ContainerRegistrationDialogComponent {
  protected readonly containerService: ContainerServiceInterface =
    inject(ContainerService);
  public readonly data: {
    response: PiResponse<ContainerRegisterData>;
    containerSerial: WritableSignal<string>;
    selectedContent: WritableSignal<string>;
  } = inject(MAT_DIALOG_DATA);

  constructor(private dialogRef: MatDialogRef<LostTokenComponent>) {
    this.dialogRef.afterClosed().subscribe(() => {
      this.containerService.stopPolling();
    });
  }

  containerSelected(containerSerial: string) {
    this.dialogRef.close();
    this.data.selectedContent.set('container_details');
    this.data.containerSerial.set(containerSerial);
  }
}
