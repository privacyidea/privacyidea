import { Component, inject, WritableSignal } from "@angular/core";
import {
  MAT_DIALOG_DATA,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle
} from "@angular/material/dialog";
import { PiResponse } from "../../../../app.component";
import {
  ContainerRegisterData,
  ContainerService,
  ContainerServiceInterface
} from "../../../../services/container/container.service";
import { LostTokenComponent } from "../../token-card/token-tab/lost-token/lost-token.component";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "../../../../app.routes";
import { MatButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";

export type ContainerCreationDialogData = {
  response: PiResponse<ContainerRegisterData>;
  containerSerial: WritableSignal<string>;
  registerContainer: (containerSerial: string) => void;
};

@Component({
  selector: "app-container-registration-dialog",
  imports: [MatDialogContent, MatDialogTitle, MatButton, MatIcon],
  templateUrl: "./container-registration-dialog.component.html",
  styleUrl: "./container-registration-dialog.component.scss"
})
export class ContainerRegistrationDialogComponent {
  protected readonly containerService: ContainerServiceInterface =
    inject(ContainerService);
  public readonly data: ContainerCreationDialogData = inject(MAT_DIALOG_DATA);
  private router = inject(Router);

  constructor(private dialogRef: MatDialogRef<LostTokenComponent>) {
    this.dialogRef.afterClosed().subscribe(() => {
      this.containerService.stopPolling();
    });
  }

  containerSelected(containerSerial: string) {
    this.dialogRef.close();
    this.router.navigateByUrl(
      ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + containerSerial
    );
    this.data.containerSerial.set(containerSerial);
  }

  regenerateQRCode() {
    this.data.registerContainer(this.data.containerSerial());
    this.dialogRef.close();
  }
}
