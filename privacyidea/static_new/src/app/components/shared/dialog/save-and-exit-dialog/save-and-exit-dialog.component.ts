import { Component, computed } from "@angular/core";
import { DialogWrapperComponent } from "../dialog-wrapper/dialog-wrapper.component";
import { AbstractDialogComponent } from "../abstract-dialog/abstract-dialog.component";
import { DialogAction } from "../../../../models/dialog";
import { NAVIGATION_BLOCKING_DIALOG_CLASS } from "../../../../constants/global.constants";

export interface SaveAndExitDialogData {
  title?: string;
  message?: string;
  saveButtonText?: string;
  discardButtonText?: string;
  allowSaveExit: boolean;
  saveExitDisabled: boolean;
}

export type SaveAndExitDialogResult = "discard" | "save-exit";

@Component({
  selector: "app-save-and-exit-dialog",
  host: { class: NAVIGATION_BLOCKING_DIALOG_CLASS },
  templateUrl: "./save-and-exit-dialog.component.html",
  styleUrls: ["./save-and-exit-dialog.component.scss"],
  standalone: true,
  imports: [DialogWrapperComponent]
})
export class SaveAndExitDialogComponent extends AbstractDialogComponent<
  SaveAndExitDialogData,
  SaveAndExitDialogResult
> {
  constructor() {
    super();
    this.dialogRef.disableClose = true;
  }

  actions = computed<DialogAction<SaveAndExitDialogResult>[]>(() => [
    {
      label: this.data.saveButtonText || $localize`Save`,
      value: "save-exit",
      type: "confirm",
      icon: "save",
      disabled: this.data.saveExitDisabled,
      hidden: !this.data.allowSaveExit,
    },
    {
      label: this.data.discardButtonText || $localize`Discard`,
      value: "discard",
      type: "destruct",
      primary: true
    }
  ]);

  title = computed(() => this.data.title || $localize`Discard changes`);
  message = computed(
    () => this.data.message || $localize`You have unsaved changes. Do you want to save them before exiting?`
  );

  onAction(result: SaveAndExitDialogResult): void {
    this.dialogRef.close(result);
  }
}
