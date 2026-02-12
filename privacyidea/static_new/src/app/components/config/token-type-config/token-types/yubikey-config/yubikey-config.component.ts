import { Component, input, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-yubikey-config',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule
  ],
  templateUrl: './yubikey-config.component.html',
  styles: `
    :host {
      display: block;
    }
  `
})
export class YubikeyConfigComponent {
  formData = input.required<Record<string, any>>();
  yubikeyApiIds = input.required<string[]>();

  onYubikeyCreateNewKey = output<string>();
  onDeleteEntry = output<string>();

  newYubikeyApiId = signal('');

  createNewKey() {
    if (this.newYubikeyApiId()) {
      this.onYubikeyCreateNewKey.emit(this.newYubikeyApiId());
      this.newYubikeyApiId.set('');
    }
  }

  deleteEntry(key: string) {
    this.onDeleteEntry.emit(key);
  }
}
