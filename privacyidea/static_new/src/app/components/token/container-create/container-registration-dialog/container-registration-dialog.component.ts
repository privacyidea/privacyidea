import { Component, Inject, WritableSignal } from '@angular/core';
import {
  MAT_DIALOG_DATA,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';
import { LostTokenComponent } from '../../token-card/token-tab/lost-token/lost-token.component';
import {
  ContainerRegisterData,
  ContainerService,
} from '../../../../services/container/container.service';
import { PiResponse } from '../../../../app.component';

@Component({
  selector: 'app-container-registration-dialog',
  imports: [MatDialogContent, MatDialogTitle],
  templateUrl: './container-registration-dialog.component.html',
  styleUrl: './container-registration-dialog.component.scss',
})
export class ContainerRegistrationDialogComponent {
  constructor(
    protected containerService: ContainerService,
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
