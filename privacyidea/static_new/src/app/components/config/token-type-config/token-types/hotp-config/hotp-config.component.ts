import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';

@Component({
  selector: 'app-hotp-config',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatSelectModule
  ],
  templateUrl: './hotp-config.component.html',
  styles: `
    :host {
      display: block;
    }
  `
})
export class HotpConfigComponent {
  formData = input.required<Record<string, any>>();
  hashLibs = input.required<string[]>();
}
