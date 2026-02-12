import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

@Component({
  selector: 'app-tiqr-config',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule
  ],
  templateUrl: './tiqr-config.component.html',
  styleUrl: './tiqr-config.component.scss'
})
export class TiqrConfigComponent {
  formData = input.required<Record<string, any>>();
}
