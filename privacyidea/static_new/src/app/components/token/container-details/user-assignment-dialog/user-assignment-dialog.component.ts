import { Component, signal, WritableSignal, computed } from '@angular/core';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { FormsModule } from '@angular/forms';
import { MatIcon, MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-user-assignment-dialog',
  templateUrl: './user-assignment-dialog.component.html',
  styleUrls: ['./user-assignment-dialog.component.scss'],
  standalone: true,
  imports: [
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    FormsModule,
    MatDialogModule,
    MatIconModule,
  ],
})
export class UserAssignmentDialogComponent {
  pin: WritableSignal<string> = signal('');
  pinRepeat: WritableSignal<string> = signal('');
  hidePin: WritableSignal<boolean> = signal(true);

  pinsMatch = computed(() => this.pin() === this.pinRepeat());

  constructor(
    public dialogRef: MatDialogRef<
      UserAssignmentDialogComponent,
      string | null
    >,
  ) {}

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
