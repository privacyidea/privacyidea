import { Component, input, output } from "@angular/core";
import { assert } from "../../../../utils/assert";
import { DialogAction } from "../../../../models/dialog";
import { CommonModule } from "@angular/common";
import { MatDialogModule } from "@angular/material/dialog";

@Component({
  selector: "app-dialog-wrapper",
  templateUrl: "./dialog-wrapper.component.html",
  standalone: true,
  imports: [CommonModule, MatDialogModule],
  styleUrls: ["./dialog-wrapper.component.scss"]
})
export class DialogWrapperComponent<R = any> {
  title = input.required<string>();
  showCloseButton = input<boolean>(true);
  cancelButtonLabel = input<string>("Cancel");
  actions = input<DialogAction<R>[]>([]);
  actionExecuted = output<R>();
  close = output<void>();

  onActionClick(action: DialogAction<R>): void {
    this.actionExecuted.emit(action.value);
  }

  onCloseClick(): void {
    this.close.emit();
  }

  ngOnInit() {
    assert(
      this.actions().length != 0 || this.showCloseButton(),
      "Dialog must have at least one action or a close button."
    );
  }
}
