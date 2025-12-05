import { Directive, inject } from "@angular/core";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";

// Wichtig: Keine @Component-Metadaten hier, wenn Sie nur eine abstrakte Basisklasse/Interface wollen.
// Hinweis: Da MatDialog.open() ComponentType<any> erwartet, muss die ENDKLASSE ein @Component sein.
@Directive() // Verwenden Sie @Directive(), um die Klasse als injizierbar zu kennzeichnen, aber nicht als Komponente zu registrieren.
export abstract class AbstractDialogComponent<T = any, R = any> {
  /** * Die injizierten Daten. Durch die Initialisierung im Konstruktor erzwingen wir,
   * dass jede erbende Klasse diese Struktur (title, content, etc.) in ihren Daten erwarten muss.
   */
  public readonly data: T = inject(MAT_DIALOG_DATA);

  /** * Die Referenz zum Steuern des Dialogs.
   */

  protected dialogRef: MatDialogRef<T, R> = inject(MatDialogRef);

  /**
   * Basisimplementierung zum Schließen des Dialogs ohne Rückgabewert.
   */
  protected close(dialogResult?: R | undefined): void {
    this.dialogRef.close(dialogResult);
  }
}
