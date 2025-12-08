import { Directive, inject } from "@angular/core";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";

@Directive()
export abstract class AbstractDialogComponent<T = any, R = any> {
  /**
   * The injected data. By initializing it in the constructor, we enforce
   * that any inheriting class must expect this structure (title, content, etc.) in its data.
   */
  public readonly data: T = inject(MAT_DIALOG_DATA);
  protected dialogRef: MatDialogRef<T, R> = inject(MatDialogRef);

  /**
   * Closes the dialog with an optional result.
   * @param dialogResult  - The result to return when the dialog is closed.
   */
  protected close(dialogResult?: R | undefined): void {
    this.dialogRef.close(dialogResult);
  }
}
