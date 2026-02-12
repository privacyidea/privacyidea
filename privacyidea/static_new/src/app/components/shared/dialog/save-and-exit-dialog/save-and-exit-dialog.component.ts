import { Component, computed } from "@angular/core";
import { DialogWrapperComponent } from "../dialog-wrapper/dialog-wrapper.component";
import { AbstractDialogComponent } from "../abstract-dialog/abstract-dialog.component";
import { DialogAction } from "../../../../models/dialog";

export interface SaveAndExitDialogData {
  title: string;
  message: string;
  saveButtonText?: string;
  discardButtonText?: string;
  cancelButtonText?: string;
  allowSaveExit: boolean;
  saveExitDisabled: boolean;
}

export type SaveAndExitDialogResult = "discard" | "save-exit";

@Component({
  selector: "app-save-and-exit-dialog",
  templateUrl: "./save-and-exit-dialog.component.html",
  styleUrls: ["./save-and-exit-dialog.component.scss"],
  standalone: true,
  imports: [DialogWrapperComponent]
})
export class SaveAndExitDialogComponent extends AbstractDialogComponent<
  SaveAndExitDialogData,
  SaveAndExitDialogResult
> {
  actions = computed<DialogAction<SaveAndExitDialogResult>[]>(() => {
    if (this.data.allowSaveExit) {
      return [
        { label: this.data.discardButtonText || ("Discard" as any), value: "discard", type: "destruct" },
        {
          label: this.data.saveButtonText || ("Save & Exit" as any),
          value: "save-exit",
          type: "confirm",
          disabled: this.data.saveExitDisabled,
          show: this.data.allowSaveExit
        }
      ];
    } else {
      return [{ label: this.data.discardButtonText || ("Discard" as any), value: "discard", type: "destruct" }];
    }
  });

  onAction(result: SaveAndExitDialogResult): void {
    this.dialogRef.close(result);
  }
}
