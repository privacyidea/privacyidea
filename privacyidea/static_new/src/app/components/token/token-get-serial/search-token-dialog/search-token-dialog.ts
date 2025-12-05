import { Component } from "@angular/core";
import { DialogWrapperComponent } from "../../../shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { AbstractDialogComponent } from "../../../shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogAction } from "../../../../models/dialog";

@Component({
  selector: "app-search-token-dialog",
  templateUrl: "./search-token-dialog.html",
  styleUrl: "./search-token-dialog.scss",
  standalone: true,
  imports: [DialogWrapperComponent]
})
export class SearchTokenDialogComponent extends AbstractDialogComponent<string> {
  action: DialogAction<true> = {
    label: $localize`Start Search`,
    value: true,
    type: "confirm",
    closeOnAction: true
  };
}
