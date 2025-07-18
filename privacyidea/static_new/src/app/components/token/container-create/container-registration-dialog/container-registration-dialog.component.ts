import { Component, Inject, WritableSignal } from '@angular/core';
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
  constructor(
    @Inject(ContainerService)
    protected containerService: ContainerServiceInterface,
    private dialogRef: MatDialogRef<LostTokenComponent>,
    @Inject(MAT_DIALOG_DATA)
    public data: {
      response: PiResponse<ContainerRegisterData>;
      containerSerial: WritableSignal<string>;
      selectedContent: WritableSignal<string>;
    },
  ) {
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
