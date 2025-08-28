import { Component, computed, inject, signal, WritableSignal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatDialogModule, MatDialogRef } from "@angular/material/dialog";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";

@Component({
  selector: "app-user-assignment-dialog",
  templateUrl: "./user-assignment-dialog.component.html",
  styleUrls: ["./user-assignment-dialog.component.scss"],
  standalone: true,
  imports: [MatFormFieldModule, MatInputModule, MatButtonModule, FormsModule, MatDialogModule, MatIconModule]
})
export class UserAssignmentDialogComponent {
  public dialogRef = inject(MatDialogRef<UserAssignmentDialogComponent, string | null>);
  pin: WritableSignal<string> = signal("");
  pinRepeat: WritableSignal<string> = signal("");
  hidePin: WritableSignal<boolean> = signal(true);
  pinsMatch = computed(() => this.pin() === this.pinRepeat());

  togglePinVisibility(): void {
    this.hidePin.update((prev) => !prev);
  }

  onConfirm(): void {
    if (this.pinsMatch()) {
      this.dialogRef.close(this.pin());
    }
  }

  onCancel(): void {
    this.dialogRef.close(null);
  }
}
