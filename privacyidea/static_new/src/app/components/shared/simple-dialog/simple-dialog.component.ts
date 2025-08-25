import { Component, inject } from "@angular/core";
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent, MatDialogTitle
} from "@angular/material/dialog";
import { MatButton } from "@angular/material/button";

export type SimpleDialogData = {
  header: string | null;
  text: string;
  data: string;
};

@Component({
  selector: "app-simple-dialog",
  imports: [
    MatDialogContent,
    MatButton,
    MatDialogActions,
    MatDialogClose,
    MatDialogTitle
  ],
  templateUrl: "./simple-dialog.component.html",
  styleUrl: "./simple-dialog.component.scss"
})
export class SimpleDialogComponent {
  public readonly data = inject(MAT_DIALOG_DATA);
}
