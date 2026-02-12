import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

@Component({
  selector: 'app-u2f-config',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule
  ],
  templateUrl: './u2f-config.component.html',
  styleUrl: './u2f-config.component.scss'
})
export class U2fConfigComponent {
  formData = input.required<Record<string, any>>();
}
